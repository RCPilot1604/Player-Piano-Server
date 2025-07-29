from flask import Flask
from flask import request, jsonify, current_app
import json
import os
from datetime import datetime
import logging
import flask_socketio
from flask_socketio import join_room, leave_room
from alsa_midi import SequencerClient, NoteOnEvent, NoteOffEvent, ControlChangeEvent
import time
from flask_cors import CORS
from threading import Thread
from midi_parser import MidiParser
from instruments import GeneralMidiInstrument

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MidiPlayerGateway:

    def __init__(self, socket):
        self.current_song = None
        self.volume = 100
        self.position = 0
        self.playback_start_time = None
        self.current_events = []
        self.playback_thread = None
        self.interval_timer = None
        self.last_percentage = -1
        self.parser = None
        self.alsa_player = None
        self.track_names = None
        self.tracks_to_play = []
        self.total_duration = 0.0 # Total duration of the MIDI file in ms
        # Player thread
        self.player_thread = None
        self.pause_event = True # default set to PAUSE
        self.stop_event = True
        self.port = None  # ALSA port for MIDI output
        self.midi_idx = None  # Current position in the MIDI file
        self.socket = socket
        # For logging MIDI events
        self.midi_log_path = None
    

    def player_thread_function(self, socketio):
        """Thread function to handle playback logic"""
        client = SequencerClient("Player Piano")
        while True:
            if self.stop_event: 
                self.midi_idx = 0
                self.socket.emit('playback_finished', room='midi_players')
                break
            while self.pause_event:
                pass # Do nothing; halt the execution
            if self.midi_idx >= len(self.current_events):
                self.pause_event = True
                self.midi_idx = 0
                self.socket.emit('playback_finished', room='midi_players')
                break
            event = self.current_events[self.midi_idx]
            # Playback logic here
            event_to_send = None
            if(event.isBounceBack):
                event_to_send = ControlChangeEvent(controller=110, value=event.note, channel=0)
            else:
                event_to_send = NoteOnEvent(note=event.note, velocity=event.velocity) if event.type == 'note_on' else NoteOffEvent(note=event.note, velocity=event.velocity)
            if event_to_send:
                client.event_output(event_to_send)
                self.midi_idx += 1
                self.socket.emit('timeUpdate', (event.timestamp / self.total_duration) * 100, room='midi_players')
                print("Heartbeat: ", event.timestamp, "DeltaT: ", event.deltaT)
                time.sleep(event.deltaT / 1000.0)  # Convert deltaT to seconds

    def parse_song(self, tracks_to_play):
        """Parse the MIDI file and filter tracks based on selected instruments"""
        try:
            parsed_events = self.parser._parse_to_events(tracks_to_play) # Parse raw MIDI file
            sanitized_events = self.parser._sanitize_events(parsed_events) # Sanitize events
            self.current_events = self.parser._convert_events(sanitized_events) # Convert to MidiEvent objects
            self.parser._export_to_json(self.current_events)
            self.total_duration = self.parser._calculate_duration(self.current_events)  # Get total duration in ms
            self.player_thread = Thread(target=self.player_thread_function, args=(self.socket,))
            self.stop_event = False
            self.pause_event = True
            self.midi_idx = 0
            self.player_thread.start() #start the player thread whenever 
            return True
        except Exception as e:
            logger.error(f"Error parsing MIDI file: {e}")
            self.socket.emit('error', {'message': f'Failed to parse MIDI file: {str(e)}'})
            return False
        
    def load_song(self, song_path: str, song_data: dict = None):
        """Load a MIDI song for playback"""
        # Clear the current running player thread 
        if self.player_thread and self.player_thread.is_alive():
            self.stop_event = True
            self.player_thread.join()
        # Parse MIDI file into ./tmp/midi_events.json which merely serves as staging ground 
        try:
            self.parser = MidiParser(song_path)
            self.parser._load_midi()
            self.current_song = song_data
            self.position = 0
            self.pause_event = True
                        
            # Update the checkboxes to select tracks
            with open('./tmp/tracks.json', 'r') as f:
                file_data = json.load(f)
                data = file_data.items()
                print(data)
                instrument_names = [{"id": i, "channel": i[0], "name": GeneralMidiInstrument.get_instrument_name(i[1])} for i in data]
                self.socket.emit('instruments', instrument_names, room='midi_players')

            return True
        except Exception as e:
            logger.error(f"Error loading song: {e}")
            self.socket.emit('error', {'message': f'Failed to load song: {str(e)}'})
            return False
    
    def play(self):
        self.pause_event = False
    
    def pause(self):
        self.pause_event = True
    
    def seek(self, position: int):
        # The idea for seek is that we find the event with the closest time_ms and set the index to that event
        if not self.current_events:
            logger.warning("No MIDI events loaded for seeking")
            return
        position_ms = (position / 100) * self.total_duration  # Convert percentage to ms
        closest_event = min(self.current_events, key=lambda e: abs(e.time_ms - position_ms))
        self.midi_idx = self.current_events.index(closest_event)

    def close(self):
        if self.alsa_player:
            self.alsa_player.stdin.write("QUIT\n")
            self.alsa_player.stdin.flush()
            self.alsa_player.wait()
    
    def set_volume(self, volume: int):
        """Set playback volume"""
        self.volume = max(0, min(100, volume))
        # Don't emit here, let the WebSocket handler emit the event
    
    def update_position(self, position: int):
        """Update current playback position and emit to clients"""
        self.position = position
        socket.emit('timeUpdate', position, room='midi_players')
    
    def get_status(self):
        """Get current player status"""
        return {
            'isPlaying': self.pause_event is False,
            'currentSong': self.current_song,
            'volume': self.volume,
            'position': self.position,
        }
    
    def log_event(self, event_data):
        """Log MIDI event for debugging"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'event': event_data
            }
            
            # Append to log file
            with open(self.midi_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.error(f"Error logging event: {e}")

# Global websocket instance
socket = flask_socketio.SocketIO(app)
# Global gateway instance

gateway = MidiPlayerGateway(socket)



@app.route('/')
def home():
    return 'Hello, Flask!'

@app.route('/', methods=['GET'])
def get_categories():
    """Get all categories from database"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            data = json.load(f)
        return jsonify(data.get('categories', [])), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/<int:category_id>', methods=['GET'])
def get_category(category_id):
    """Get a specific category by ID"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        
        # Find category by ID
        for category in categories:
            if category.get('id') == category_id:
                return jsonify(category), 200
        
        return jsonify({'error': 'Category not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['POST'])
def create_category():
    """Create a new category"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        # Check if category with same name already exists
        existing_categories = database.get('categories', [])
        for category in existing_categories:
            if category.get('name', '').lower() == data['name'].lower():
                return jsonify({'error': 'Category with this name already exists'}), 409
        
        # Add metadata
        data['id'] = generate_category_id(existing_categories)
        data['createdAt'] = datetime.utcnow().isoformat()
        data['updatedAt'] = datetime.utcnow().isoformat()
        
        # Add to database
        if 'categories' not in database:
            database['categories'] = []
        
        database['categories'].append(data)
        
        # Save to file
        save_database_to_file(database)
        
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """Update an existing category"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        
        # Find category by ID
        category_index = None
        for i, category in enumerate(categories):
            if category.get('id') == category_id:
                category_index = i
                break
        
        if category_index is not None:
            # Check for duplicate name (excluding current category)
            if 'name' in data:
                for i, category in enumerate(categories):
                    if (i != category_index and 
                        category.get('name', '').lower() == data['name'].lower()):
                        return jsonify({'error': 'Category with this name already exists'}), 409
            
            # Preserve original creation date and ID
            original_created_at = categories[category_index].get('createdAt')
            original_id = categories[category_index].get('id')
            
            # Update category data
            categories[category_index].update(data)
            categories[category_index]['updatedAt'] = datetime.utcnow().isoformat()
            
            # Restore original metadata
            if original_created_at:
                categories[category_index]['createdAt'] = original_created_at
            if original_id:
                categories[category_index]['id'] = original_id
            
            # Save to file
            save_database_to_file(database)
            
            return jsonify(categories[category_index]), 200
        else:
            return jsonify({'error': 'Category not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """Delete a category"""
    try:
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        songs = database.get('songs', [])
        
        # Find and remove category by ID
        deleted_category = None
        for i, category in enumerate(categories):
            if category.get('id') == category_id:
                deleted_category = categories.pop(i)
                break
        
        if deleted_category:
            # Check if any songs use this category
            songs_using_category = [
                song for song in songs 
                if song.get('category') == deleted_category.get('name')
            ]
            
            if songs_using_category:
                return jsonify({
                    'error': 'Cannot delete category. It is being used by songs.',
                    'songs_count': len(songs_using_category)
                }), 409
            
            # Save to file
            save_database_to_file(database)
            return jsonify(deleted_category), 200
        else:
            return jsonify({'error': 'Category not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/<int:category_id>/songs', methods=['GET'])
def get_songs_by_category(category_id):
    """Get all songs in a specific category"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        songs = database.get('songs', [])
        
        # Find category by ID
        category = None
        for cat in categories:
            if cat.get('id') == category_id:
                category = cat
                break
        
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        # Find songs in this category
        category_songs = [
            song for song in songs 
            if song.get('category') == category.get('name')
        ]
        
        return jsonify({
            'category': category,
            'songs': category_songs,
            'count': len(category_songs)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['GET'])
def search_categories():
    """Search categories by name"""
    try:
        query = request.args.get('q', '').lower()
        
        if not query:
            return jsonify({'error': 'Search query required'}), 400
        
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        
        # Filter categories by search query
        filtered_categories = [
            category for category in categories
            if query in category.get('name', '').lower()
        ]
        
        return jsonify(filtered_categories), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['GET'])
def get_songs():
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            data = json.load(f)
        return jsonify(data.get('songs', [])), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/<int:song_id>', methods=['GET'])
def get_song(song_id):
    """Get a specific song by ID"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        songs = database.get('songs', [])
        
        # Find song by ID
        for song in songs:
            if song.get('id') == song_id:
                return jsonify(song), 200
        
        return jsonify({'error': 'Song not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/', methods=['POST'])
def create_song():
    """Create a new song entry"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['title']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        # Add metadata
        data['id'] = generate_song_id(database.get('songs', []))
        data['createdAt'] = datetime.utcnow().isoformat()
        data['updatedAt'] = datetime.utcnow().isoformat()
        
        # Add to database
        if 'songs' not in database:
            database['songs'] = []
        
        database['songs'].append(data)
        
        # Save to file
        save_database_to_file(database)
        
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/<int:song_id>', methods=['PUT'])
def update_song(song_id):
    """Update an existing song"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        songs = database.get('songs', [])
        
        # Find song by ID instead of array index
        song_index = None
        for i, song in enumerate(songs):
            if song.get('id') == song_id:
                song_index = i
                break
        
        if song_index is not None:
            # Preserve original creation date and ID
            original_created_at = songs[song_index].get('createdAt')
            original_id = songs[song_index].get('id')
            
            # Update song data
            songs[song_index].update(data)
            songs[song_index]['updatedAt'] = datetime.utcnow().isoformat()
            
            # Restore original metadata
            if original_created_at:
                songs[song_index]['createdAt'] = original_created_at
            if original_id:
                songs[song_index]['id'] = original_id
            
            # Save to file
            save_database_to_file(database)
            
            return jsonify(songs[song_index]), 200
        else:
            return jsonify({'error': 'Song not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/<int:song_id>', methods=['DELETE'])
def delete_song(song_id):
    """Delete a song"""
    try:
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        songs = database.get('songs', [])
        
        # Find and remove song by ID
        deleted_song = None
        for i, song in enumerate(songs):
            if song.get('id') == song_id:
                deleted_song = songs.pop(i)
                break
        
        if deleted_song:
            # Save to file
            save_database_to_file(database)
            return jsonify(deleted_song), 200
        else:
            return jsonify({'error': 'Song not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['GET'])
def search_songs():
    """Search songs by title, artist, or category"""
    try:
        query = request.args.get('q', '').lower()
        category = request.args.get('category')
        
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        songs = database.get('songs', [])
        filtered_songs = songs
        
        # Filter by search query
        if query:
            filtered_songs = [
                song for song in filtered_songs
                if query in song.get('title', '').lower() or
                   query in song.get('composer', '').lower()
            ]
        
        # Filter by category
        if category:
            filtered_songs = [
                song for song in filtered_songs
                if song.get('category') == category
            ]
        
        return jsonify(filtered_songs), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_midi():
    """Upload a MIDI file and create song entry"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        if not file.filename.lower().endswith(('.mid', '.midi')):
            return jsonify({'error': 'Only MIDI files are allowed'}), 400
        
        # Save file
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Create song entry
        song_data = {
            'title': request.form.get('title', filename.replace('.mid', '').replace('.midi', '')),
            'artist': request.form.get('artist', ''),
            'category': request.form.get('category', ''),
            'filename': filename,
            'filepath': filepath,
            'filesize': os.path.getsize(filepath)
        }
        
        # Add to database
        song_data['id'] = generate_song_id_from_file()
        song_data['createdAt'] = datetime.utcnow().isoformat()
        song_data['updatedAt'] = datetime.utcnow().isoformat()
        
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        if 'songs' not in database:
            database['songs'] = []
        
        database['songs'].append(song_data)
        save_database_to_file(database)
        
        return jsonify(song_data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_category_stats():
    """Get statistics about categories and their song counts"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        songs = database.get('songs', [])
        
        # Calculate song counts per category
        category_stats = []
        for category in categories:
            song_count = sum(
                1 for song in songs 
                if song.get('category') == category.get('name')
            )
            
            category_stats.append({
                'id': category.get('id'),
                'name': category.get('name'),
                'song_count': song_count,
                'created_at': category.get('createdAt'),
                'updated_at': category.get('updatedAt')
            })
        
        # Sort by song count (descending)
        category_stats.sort(key=lambda x: x['song_count'], reverse=True)
        
        return jsonify({
            'total_categories': len(categories),
            'total_songs': len(songs),
            'category_stats': category_stats
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Helper functions
def save_database_to_file(database):
    """Save database to db.json file"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        with open(db_path, 'w') as f:
            json.dump(database, f, indent=2)
    except Exception as e:
        print(f"Error saving database: {e}")

def generate_category_id(categories):
    """Generate a unique category ID"""
    if not categories:
        return 1
    
    # Find the highest ID and add 1
    max_id = max([category.get('id', 0) for category in categories], default=0)
    return max_id + 1

def save_database_to_file(database):
    """Save database to db.json file"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        with open(db_path, 'w') as f:
            json.dump(database, f, indent=2)
    except Exception as e:
        print(f"Error saving database: {e}")

def generate_song_id(songs):
    """Generate a unique song ID from songs list"""
    if not songs:
        return 1
    
    # Find the highest ID and add 1
    max_id = max([song.get('id', 0) for song in songs], default=0)
    return max_id + 1

def generate_song_id_from_file():
    """Generate a unique song ID by reading from file"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        songs = database.get('songs', [])
        return generate_song_id(songs)
    except Exception as e:
        print(f"Error generating song ID: {e}")
        return 1

def secure_filename(filename):
    """Make filename safe for filesystem"""
    import re
    filename = re.sub(r'[^\w\s-]', '', filename).strip()
    return re.sub(r'[-\s]+', '-', filename)

# WebSocket Event Handlers
def register_websocket_events(socketio):
    """Register all WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect(auth=None):
        """Handle client connection"""
        logger.info('Client connected')
        join_room('midi_players')
        socketio.emit('connected', {'status': 'Connected to MIDI Player'})
        socketio.emit('player_status', gateway.get_status())
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info('Client disconnected')
        leave_room('midi_players')
    
    @socketio.on('loadMidi')
    def handle_load_midi(song_data):
        """Load a MIDI song for playback (matches frontend expectation)"""
        print(f"Loading MIDI song: {song_data}")
        try:
            # Extract song information from frontend format
            midi_path = song_data.get('midiPath') or song_data.get('path')
            if not midi_path or not os.path.exists(midi_path):
                socketio.emit('error', {'message': 'Song file not found'})
                print(f"Song file not found: {midi_path}")
                return

            success = gateway.load_song(midi_path, song_data)
            if success:
                # Emit event that frontend expects
                print(f"Song loaded successfully: {song_data}")
                socketio.emit('loadMidiUpdate', song_data, room='midi_players')
            else:
                print(f"Failed to load song: {song_data}")
                
        except Exception as e:
            logger.error(f"Error in loadMidi handler: {e}")
            socketio.emit('error', {'message': str(e)})
    
    @socketio.on('parseMidi')
    def handle_load_song(selected_tracks):
        """Parse MIDI file and prepare for playback"""
        selected_tracks = [int(t) for t in selected_tracks]
        try:
            success = gateway.parse_song(selected_tracks)
            if success:
                # Emit event that frontend expects
                socketio.emit('parseMidiUpdate', {'status': 'success'}, room='midi_players')
                logger.info("MIDI file parsed successfully")
            else:
                socketio.emit('error', {'message': 'Failed to parse MIDI file'})
        except Exception as e:
            logger.error(f"Error parsing MIDI file: {e}")
            socketio.emit('error', {'message': str(e)})
        
    
    @socketio.on('play')
    def handle_play(data=None):
        """Start playback"""
        try:
            gateway.play()
            gateway.playback_start_time = time.time()
            
            # Emit events that frontend expects
            socketio.emit('playUpdate', True, room='midi_players')
            socketio.emit('playback_started', {
                'song': gateway.current_song,
                'timestamp': gateway.playback_start_time
            }, room='midi_players')
            
            logger.info('Playback started')
        except Exception as e:
            logger.error(f"Error starting playback: {e}")
            socketio.emit('error', {'message': str(e)})
    
    @socketio.on('pause')
    def handle_pause(data=None):
        """Pause playback"""
        try:
            gateway.pause()
            
            # Emit events that frontend expects
            socketio.emit('playUpdate', False, room='midi_players')
            socketio.emit('playback_paused', {
                'position': gateway.position
            }, room='midi_players')
            
            logger.info('Playback paused')
        except Exception as e:
            logger.error(f"Error pausing playback: {e}")
            socketio.emit('error', {'message': str(e)})
    
    @socketio.on('stop')
    def handle_stop():
        """Stop playback"""
        try:
            gateway.pause()
            gateway.seek(0)
            gateway.position = 0
            
            socketio.emit('playback_stopped', room='midi_players')
            logger.info('Playback stopped')
        except Exception as e:
            logger.error(f"Error stopping playback: {e}")
            socketio.emit('error', {'message': str(e)})
    
    @socketio.on('seek')
    def handle_seek(seek_position):
        """Seek to position (matches frontend expectation)"""
        try:
            tick = int(seek_position) if isinstance(seek_position, (int, str)) else seek_position.get('tick', 0)
            gateway.seek(tick)
            gateway.position = tick
            
            # Emit events that frontend expects
            socketio.emit('seekUpdate', tick, room='midi_players')
            socketio.emit('timeUpdate', tick, room='midi_players')
            
            logger.info(f'Seeked to position: {tick}')
        except Exception as e:
            logger.error(f"Error seeking: {e}")
            socketio.emit('error', {'message': str(e)})
    
    @socketio.on('volume')
    def handle_volume(volume_value):
        """Set playback volume (matches frontend expectation)"""
        try:
            volume = int(volume_value) if isinstance(volume_value, (int, str)) else volume_value
            gateway.set_volume(volume)
            socketio.emit('volumeUpdate', volume, room='midi_players')
            logger.info(f'Volume set to: {volume}')
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            socketio.emit('error', {'message': str(e)})
    
    @socketio.on('set_volume')
    def handle_set_volume(data):
        """Set playback volume (alternative API)"""
        try:
            volume = data.get('volume', 100)
            gateway.set_volume(volume)
            socketio.emit('volumeUpdate', volume, room='midi_players')
            logger.info(f'Volume set to: {volume}')
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            socketio.emit('error', {'message': str(e)})
    
    @socketio.on('get_status')
    def handle_get_status():
        """Get current player status"""
        try:
            status = gateway.get_status()
            socketio.emit('player_status', status)
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            socketio.emit('error', {'message': str(e)})

    @socketio.on('setTracks')
    def handle_set_track_names(tracks):
        """Set tracks to be played for current song"""
        try:
            if not isinstance(tracks, list):
                raise ValueError("Track names must be a list")
            # Ensure all elements are ints
            tracks = [t for t in tracks if isinstance(t, int)]
            gateway.tracks_to_play = tracks
            
        except Exception as e:
            logger.error(f"Error setting track names: {e}")
            socketio.emit('error', {'message': str(e)})

if __name__ == '__main__':
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Additional configurations
    app.config['ASSETS_FOLDER'] = os.path.join(os.path.abspath(os.curdir), 'assets')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

    # Initialize extensions
    CORS(app, origins="*")
    socket.init_app(app, cors_allowed_origins="*")

    # Register WebSocket events
    register_websocket_events(socket)
    socket.run(app, host='0.0.0.0', port=5000)