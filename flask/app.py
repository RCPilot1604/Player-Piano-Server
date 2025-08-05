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
from threading import Thread, Event
from midi_parser import MidiParser
from instruments import GeneralMidiInstrument
import atexit
from settings import Settings
import traceback

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = Settings() # Global settings instance

class MidiPlayerGateway:

    def __init__(self, socket, settings):
        self.settings = settings
        self.current_song = None
        self.volume = 100
        self.playback_start_time = None
        self.current_events = []
        self.playback_thread = None
        self.interval_timer = None
        self.last_percentage = -1
        self.parser = None
        self.alsa_player = None
        self.track_names = None
        self.tracks_to_play = []
        self.tiles_to_play = None
        self.instrument_names = None
        self.total_duration = 0.0 # Total duration of the MIDI file in ms
        # Player thread
        self.pause_event = Event() # default set to PAUSE
        self.stop_event = True
        self.port = None  # ALSA port for MIDI output
        self.midi_idx = None  # Current position in the MIDI file
        self.socket = socket
        # Clock thread
        self.clock_thread = None
        self.current_time = 0
        # For logging MIDI events
        self.midi_log_path = None

    def clock_thread_function(self, socketio):
        client = SequencerClient("Player Piano")
        print(f"Current value of current_time: {self.current_time}")
        self.midi_idx = 0  # Reset index for clock thread
        while self.current_events[self.midi_idx].timestamp < self.current_time:
            self.midi_idx += 1
        # Now we assert that self.midi_idx is at the first event that is greater than or equal to current_time
        while True:
            if self.stop_event: 
                print("Exiting Clock Thread")
                break
            if self.midi_idx >= len(self.current_events):
                self.pause_event.set()
                self.midi_idx = 0
                self.current_time = 0
                socketio.emit('timeUpdate', self.current_time, room='midi_players')
                break
            while self.pause_event.is_set():
                time.sleep(0.01)  # Yield control, avoid busy-wait
            self.current_time += self.settings.settings['clock_period'] * 1000  # Convert to milliseconds
            socketio.emit('timeUpdate', self.current_time, room='midi_players')
            if self.current_events[self.midi_idx].timestamp <= self.current_time:
                event = self.current_events[self.midi_idx]
                if event.isBounceBack:
                    event_to_send = ControlChangeEvent(value=event.note, channel=0, param=0)
                else:
                    event_to_send = NoteOnEvent(note=event.note, velocity=event.velocity) if event.type == 'note_on' else NoteOffEvent(note=event.note, velocity=event.velocity)
                if event_to_send:
                    client.event_output(event_to_send)
                self.midi_idx += 1
            time.sleep(self.settings.settings['clock_period'])

    def parse_song(self, tracks_to_play):
        """Parse the MIDI file and filter tracks based on selected instruments"""
        try:
            parsed_events = self.parser._parse_to_events(tracks_to_play) # Parse raw MIDI file
            # print(f"Length of parsed events: {len(parsed_events)}")
            self.parser._export_to_json_2D(parsed_events, './tmp/midi_parsed.json') # Export to JSON for debugging
            sanitized_events = self.parser._sanitize_events(parsed_events) # Sanitize events
            self.parser._export_to_json_2D(sanitized_events, './tmp/midi_sanitized.json') # Export to JSON for debugging
            # print(f"Length of sanitized events: {len(sanitized_events)}")
            self.parser._generate_tile_data(sanitized_events) # Generate tile data for rendering
            self.socket.emit('tileUpdate', room='midi_players') # Notify frontend to update tiles
            self.current_events = self.parser._convert_events(sanitized_events) # Convert to MidiEvent objects
            self.parser._export_to_json_flatlist(self.current_events)
            self.total_duration = self.parser._calculate_duration(self.current_events)  # Get total duration in ms
            return True
        except Exception as e:
            logger.error(f"Error parsing MIDI file: {e}")
            self.socket.emit('error', {'message': f'Failed to parse MIDI file: {str(e)}'})
            return False
        
    def load_song(self, song_path: str, song_data: dict = None):
        """Load a MIDI song for playback"""
        # Parse MIDI file into ./tmp/midi_events.json which merely serves as staging ground 
        try:
            self.parser = MidiParser(song_path, self.settings)
            self.parser._load_midi()
            self.current_song = song_data
                        
            # Update the checkboxes to select tracks
            with open('./tmp/tracks.json', 'r') as f:
                file_data = json.load(f)
                data = file_data.items()
                print(data)
                self.instrument_names = [{"id": i, "channel": i[0], "name": GeneralMidiInstrument.get_instrument_name(i[1])} for i in data]
                self.socket.emit('setInstruments', self.instrument_names, room='midi_players')
            return True
        except Exception as e:
            logger.error(f"Error loading song: {e}")
            self.socket.emit('error', {'message': f'Failed to load song: {str(e)}'})
            return False

    def play(self):
        self.pause_event.clear()  # Resume playback
    
    def pause(self):
        self.pause_event.set() # Pause playback

    def seek(self, position: int):
        # The idea for seek is that we find the event with the closest time_ms and set the index to that event
        isPaused = self.pause_event.is_set()
        if isPaused: self.pause_event.clear() # Pause the playback to eliminate race conditions
        time.sleep(0.05)
        if not self.current_events:
            logger.warning("No MIDI events loaded for seeking")
            return
        position_ms = (position / 100) * self.total_duration  # Convert percentage to ms
        self.current_time = position_ms # Update current time to the timestamp of the closest event
        socket.emit('playerbarUpdate', position, room='midi_players')
        if isPaused: self.pause_event.set() # Resume the playback if it was paused

        # Restart the threads to ensure they are in sync
        self.stop_event = True
        if self.clock_thread and self.clock_thread.is_alive():
            self.clock_thread.join()
        self.stop_event = False
        self.clock_thread = Thread(target=self.clock_thread_function, args=(self.socket,))
        self.clock_thread.start()

    def close(self):
        if self.alsa_player:
            self.alsa_player.stdin.write("QUIT\n")
            self.alsa_player.stdin.flush()
            self.alsa_player.wait()
    
    def set_volume(self, volume: int):
        """Set playback volume"""
        self.volume = max(0, min(100, volume))
        # Don't emit here, let the WebSocket handler emit the event        
    
    def get_status(self):
        """Get current player status"""
        return {
            'isPlaying': not self.pause_event.is_set(),
            'currentSong': self.current_song,
            'volume': self.volume,
            'instruments': gateway.instrument_names,
            'traksToPlay': self.tracks_to_play,
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

gateway = MidiPlayerGateway(socket, settings)

def cleanup():
    if gateway.clock_thread and gateway.clock_thread.is_alive():
        gateway.stop_event = True
        gateway.clock_thread.join()

atexit.register(cleanup)

@app.route('/')
def home():
    return 'Hello, Flask!'

@app.route('/api/tiles/', methods=['GET'])
def get_tiles():
    try:
        tiles = None
        with open(settings.settings['midi_tile_data_file_path'], 'r') as f:
            tiles = json.load(f)
        return jsonify(tiles), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/', methods=['GET'])
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

@app.route('/api/categories/', methods=['POST'])
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

@app.route('/api/crud/', methods=['GET'])
def get_songs():
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            data = json.load(f)
        return jsonify(data.get('songs', [])), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/crud/', methods=['POST'])
def create_song():
    """Create a new song entry"""
    try:
        data = request.form.to_dict()
        file = request.files.get('midiFile')
        if not data:
            print("No data provided for song creation")
            return jsonify({'error': 'No data provided'}), 400
        if not file:
            print("No MIDI file provided for song creation")
            return jsonify({'error': 'No MIDI file provided'}), 400
        
        # Validate required fields
        required_fields = ['title', 'composer', 'category', 'midiPath']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        midi_folder = os.path.join(assets_folder, 'midi')
        if not os.path.exists(midi_folder):
            os.makedirs(midi_folder)

        with open(db_path, 'r') as f:
            database = json.load(f)

        # Add metadata
        data['id'] = generate_song_id(database.get('songs', []))
        data['midiPath'] = os.path.join(midi_folder, secure_filename(file.filename))

        # Add to database
        if 'songs' not in database:
            database['songs'] = []
        
        database['songs'].append(data)
        
        # Save to file
        save_database_to_file(database)
        # Save midi file
        with open(os.path.join(midi_folder, secure_filename(file.filename)), 'wb') as f:
            file.save(f)
        
        return jsonify(data), 201
    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/crud/<int:song_id>/', methods=['DELETE'])
def delete_song(song_id):
    """Delete a song"""
    try:
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        songs = database.get('songs', [])
        
        # Find and remove song by ID, updating all following IDs
        deleted_song = None
        for i, song in enumerate(songs):
            if song.get('id') == song_id:
                deleted_song = songs.pop(i)
            if deleted_song:
                song['id'] = i-1  # Update IDs after deletion

        if deleted_song:
            # Save to file
            save_database_to_file(database)
            # Delete the MIDI file from filesystem
            midi_path = deleted_song.get('midiPath')
            if midi_path and os.path.exists(midi_path):
                os.remove(midi_path)
                socket.emit('songUpdate', )
                return jsonify({'status': 'ok'}), 200 # If the song was deleted successfully
            else: 
                return jsonify({'error': 'MIDI file not found'}), 404
        else:
            return jsonify({'error': 'Song not found'}), 404
        
        # Now go ahead and delete the file from filesystem
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

def secure_filename(filename):
    """Make filename safe for filesystem"""
    import re
    filename = re.sub(r'[^\w\s.-]', '', filename).strip()
    return re.sub(r'[-\s]+', '-', filename)

# WebSocket Event Handlers
def register_websocket_events(socketio):
    """Register all WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect(auth=None): 
    # When a client connects, we need to send over a packet that represents the entire state of the player
        """Handle client connection"""
        logger.info('Client connected')
        join_room('midi_players')
        current_status = gateway.get_status() # Get current status and update frontend
        socketio.emit('songUpdate', current_status['currentSong'], room='midi_players') # Send current song info
        socketio.emit('instrumentsUpdate', current_status['instruments'], room='midi_players') # Send current instruments info
        socketio.emit('setInstruments', current_status['tracksToPlay'], room='midi_players') # Send current instruments info
        socketio.emit('playUpdate', current_status['isPlaying'], room='midi_players') # Send playback status
        socketio.emit('volumeUpdate', current_status['volume'], room='midi_players') # Send current volume
        if gateway.tiles_to_play is not None: # If there are tiles to play, send them
            socketio.emit('tileUpdate', room='midi_players') # Notify frontend to update tiles

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
            
            socketio.emit('playback_stopped', room='midi_players')
            logger.info('Playback stopped')
        except Exception as e:
            logger.error(f"Error stopping playback: {e}")
            socketio.emit('error', {'message': str(e)})
    
    @socketio.on('seek')
    def handle_seek(seek_position):
        """Seek to position (matches frontend expectation)"""
        try:
            gateway.seek(seek_position)
            logger.info(f'Seeked to position: {seek_position}%')
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
    
    @socketio.on('get_status') # Unused at the moment
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
    gateway.stop_event = False
    gateway.pause_event.set()  # Start in paused state
    gateway.midi_idx = 0
    gateway.clock_thread = Thread(target=gateway.clock_thread_function, args=(socket,))
    gateway.clock_thread.start()
    socket.run(app, host='0.0.0.0', port=5000)