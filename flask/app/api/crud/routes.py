from flask import request, jsonify, current_app
from app.api.crud import bp
import json
import os
from datetime import datetime

@bp.route('/', methods=['GET'])
def get_songs():
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            data = json.load(f)
        return jsonify(data.get('songs', [])), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:song_id>', methods=['GET'])
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

@bp.route('/', methods=['POST'])
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

@bp.route('/<int:song_id>', methods=['PUT'])
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

@bp.route('/<int:song_id>', methods=['DELETE'])
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

@bp.route('/search', methods=['GET'])
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

@bp.route('/upload', methods=['POST'])
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