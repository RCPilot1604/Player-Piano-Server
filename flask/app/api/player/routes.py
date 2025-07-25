from flask import request, jsonify, current_app
from app.api.player import bp
import json
import os
from datetime import datetime

# Global player state (for REST API information only)
player_state = {
    'currentSong': None,
    'loaded': False,
    'volume': 100
}

@bp.route('/status', methods=['GET'])
def get_player_status():
    """Get current player status (read-only)"""
    try:
        return jsonify(player_state), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/load', methods=['POST'])
def load_midi():
    """Load a MIDI file for playback (prepare song info only)"""
    try:
        data = request.json
        if not data or 'songId' not in data:
            return jsonify({'error': 'Song ID required'}), 400
        
        song_id = data['songId']
        
        # Get song from database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        songs = database.get('songs', [])
        
        # Find song by ID
        selected_song = None
        for song in songs:
            if song.get('id') == song_id:
                selected_song = song
                break
        
        if not selected_song:
            return jsonify({'error': 'Song not found'}), 404
        
        # Check if MIDI file exists
        midi_path = selected_song.get('midiPath', '')
        if midi_path.startswith('./'):
            midi_path = midi_path[2:]  # Remove './' prefix
        
        full_midi_path = os.path.join(assets_folder, midi_path)
        
        if not os.path.exists(full_midi_path):
            return jsonify({'error': 'MIDI file not found'}), 404
        
        # Update player state (info only, actual playback via WebSocket)
        global player_state
        player_state.update({
            'currentSong': selected_song,
            'loaded': True
        })
        
        return jsonify({
            'message': 'MIDI file ready for playback',
            'song': selected_song,
            'filePath': full_midi_path
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/current-song', methods=['GET'])
def get_current_song():
    """Get currently loaded song information"""
    try:
        if not player_state['loaded'] or not player_state['currentSong']:
            return jsonify({'message': 'No song loaded', 'song': None}), 200
        
        return jsonify({
            'song': player_state['currentSong'],
            'loaded': player_state['loaded']
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/playlist', methods=['GET'])
def get_playlist():
    """Get all available songs for the playlist"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        songs = database.get('songs', [])
        
        # Add playable status to each song
        playlist = []
        for song in songs:
            midi_path = song.get('midiPath', '')
            if midi_path.startswith('./'):
                midi_path = midi_path[2:]
            
            full_midi_path = os.path.join(assets_folder, midi_path)
            is_playable = os.path.exists(full_midi_path)
            
            playlist.append({
                **song,
                'isPlayable': is_playable,
                'isCurrentSong': (player_state['currentSong'] and 
                                player_state['currentSong'].get('id') == song.get('id'))
            })
        
        return jsonify({
            'playlist': playlist,
            'total': len(playlist),
            'playable': sum(1 for song in playlist if song['isPlayable'])
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/next-song-info', methods=['GET'])
def get_next_song_info():
    """Get information about the next song in playlist"""
    try:
        if not player_state['currentSong']:
            return jsonify({'error': 'No current song'}), 400
        
        # Get playlist
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        songs = database.get('songs', [])
        current_id = player_state['currentSong'].get('id')
        
        # Find current song index
        current_index = None
        for i, song in enumerate(songs):
            if song.get('id') == current_id:
                current_index = i
                break
        
        if current_index is None:
            return jsonify({'error': 'Current song not found in playlist'}), 400
        
        # Get next song (loop to beginning if at end)
        next_index = (current_index + 1) % len(songs)
        next_song = songs[next_index]
        
        return jsonify({
            'nextSong': next_song,
            'isLastSong': current_index == len(songs) - 1
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/previous-song-info', methods=['GET'])
def get_previous_song_info():
    """Get information about the previous song in playlist"""
    try:
        if not player_state['currentSong']:
            return jsonify({'error': 'No current song'}), 400
        
        # Get playlist
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        songs = database.get('songs', [])
        current_id = player_state['currentSong'].get('id')
        
        # Find current song index
        current_index = None
        for i, song in enumerate(songs):
            if song.get('id') == current_id:
                current_index = i
                break
        
        if current_index is None:
            return jsonify({'error': 'Current song not found in playlist'}), 400
        
        # Get previous song (loop to end if at beginning)
        prev_index = (current_index - 1) % len(songs)
        prev_song = songs[prev_index]
        
        return jsonify({
            'previousSong': prev_song,
            'isFirstSong': current_index == 0
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Helper functions
def get_midi_duration(midi_path):
    """Get MIDI file duration in seconds (placeholder)"""
    try:
        # This would integrate with your MIDI parser
        # from app.parsers.midi_parser import MidiParser
        # parser = MidiParser()
        # return parser.get_duration(midi_path)
        return 120.0  # Default 2 minutes
    except Exception as e:
        print(f"Error getting MIDI duration: {e}")
        return 0.0