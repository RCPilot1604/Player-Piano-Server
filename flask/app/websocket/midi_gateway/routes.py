from flask import current_app
from flask_socketio import emit, disconnect, join_room, leave_room
import json
import subprocess
import os
import time
from threading import Thread, Timer
from datetime import datetime
import logging
from ...parsers.midi_parser import MidiParser
from ...parsers.midi_events import MidiEvent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MidiPlayerGateway:
    def __init__(self):
        self.is_playing = False
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
        
        # For logging MIDI events
        self.midi_log_path = None
        self.initialize_midi_log()
    
    def initialize_midi_log(self):
        """Initialize MIDI event logging"""
        log_dir = os.path.join(os.path.dirname(__file__), '../../..', 'server', 'midi-logs')
        os.makedirs(log_dir, exist_ok=True)
        self.midi_log_path = os.path.join(log_dir, 'midi-events.json')
    
    def load_song(self, song_path: str, song_data: dict = None):
        """Load a MIDI song for playback"""
        try:
            self.parser = MidiParser(song_path)
            print("Successfully parsed MIDI file")
            self.current_song = song_data
            self.current_events = self.parser.get_playback_events()
            self.position = 0
            self.is_playing = False
            
            # Export events for ALSA player
            self._export_events()
            print("Successfully exported events")
            # Initialize ALSA player
            self._start_alsa_player()
            print("Successfully started ALSA MIDI file")
            
            logger.info(f"Song loaded: {len(self.current_events)} events")
            emit('song_loaded', {
                'song': song_data,
                'duration': self.parser.duration,
                'events': len(self.current_events)
            })
            
            return True
        except Exception as e:
            logger.error(f"Error loading song: {e}")
            emit('error', {'message': f'Failed to load song: {str(e)}'})
            return False
    
    def _export_events(self):
        """Export parsed events for ALSA player"""
        events_data = self.parser.export_for_alsa()
        with open('./tmp/midi_events.json', 'w') as f:
            json.dump(events_data, f)
    
    def _start_alsa_player(self):
        """Start the C++ ALSA player process"""
        self.alsa_player = subprocess.Popen([
            './ALSA/alsa_midi_player',  # Your compiled C++ binary
            './tmp/midi_events.json'
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    
    def play(self):
        if self.alsa_player:
            self.alsa_player.stdin.write("PLAY\n")
            self.alsa_player.stdin.flush()
    
    def pause(self):
        if self.alsa_player:
            self.alsa_player.stdin.write("PAUSE\n")
            self.alsa_player.stdin.flush()
    
    def seek(self, tick: int):
        if self.alsa_player:
            self.alsa_player.stdin.write(f"SEEK {tick}\n")
            self.alsa_player.stdin.flush()
    
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
        # This would be called by your ALSA player or timing mechanism
        from flask_socketio import emit
        emit('timeUpdate', position, room='midi_players')
    
    def get_status(self):
        """Get current player status"""
        return {
            'isPlaying': self.is_playing,
            'currentSong': self.current_song,
            'volume': self.volume,
            'position': self.position,
            'duration': self.parser.duration if self.parser else 0
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

# Global gateway instance
gateway = MidiPlayerGateway()

# WebSocket Event Handlers
def register_websocket_events(socketio):
    """Register all WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info('Client connected')
        join_room('midi_players')
        emit('connected', {'status': 'Connected to MIDI Player'})
        emit('player_status', gateway.get_status())
    
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
                emit('error', {'message': 'Song file not found'})
                print(f"Song file not found: {midi_path}")
                return

            success = gateway.load_song(midi_path, song_data)
            if success:
                # Emit event that frontend expects
                print(f"Song loaded successfully: {song_data}")
                emit('loadMidiUpdate', song_data, room='midi_players')
            else:
                print(f"Failed to load song: {song_data}")
                
        except Exception as e:
            logger.error(f"Error in loadMidi handler: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('load_song')
    def handle_load_song(data):
        """Load a song for playback (alternative API)"""
        try:
            song_id = data.get('songId')
            song_path = data.get('path')
            song_data = data.get('songData', {})
            
            if not song_path or not os.path.exists(song_path):
                emit('error', {'message': 'Song file not found'})
                return
            
            success = gateway.load_song(song_path, song_data)
            if success:
                emit('song_loaded', {
                    'songId': song_id,
                    'songData': song_data
                }, room='midi_players')
        except Exception as e:
            logger.error(f"Error in load_song handler: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('play')
    def handle_play(data=None):
        """Start playback"""
        try:
            gateway.play()
            gateway.is_playing = True
            gateway.playback_start_time = time.time()
            
            # Emit events that frontend expects
            emit('playUpdate', True, room='midi_players')
            emit('playback_started', {
                'song': gateway.current_song,
                'timestamp': gateway.playback_start_time
            }, room='midi_players')
            
            logger.info('Playback started')
        except Exception as e:
            logger.error(f"Error starting playback: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('pause')
    def handle_pause(data=None):
        """Pause playback"""
        try:
            gateway.pause()
            gateway.is_playing = False
            
            # Emit events that frontend expects
            emit('playUpdate', False, room='midi_players')
            emit('playback_paused', {
                'position': gateway.position
            }, room='midi_players')
            
            logger.info('Playback paused')
        except Exception as e:
            logger.error(f"Error pausing playback: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('stop')
    def handle_stop():
        """Stop playback"""
        try:
            gateway.pause()
            gateway.seek(0)
            gateway.is_playing = False
            gateway.position = 0
            
            emit('playback_stopped', room='midi_players')
            logger.info('Playback stopped')
        except Exception as e:
            logger.error(f"Error stopping playback: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('seek')
    def handle_seek(seek_position):
        """Seek to position (matches frontend expectation)"""
        try:
            tick = int(seek_position) if isinstance(seek_position, (int, str)) else seek_position.get('tick', 0)
            gateway.seek(tick)
            gateway.position = tick
            
            # Emit events that frontend expects
            emit('seekUpdate', tick, room='midi_players')
            emit('timeUpdate', tick, room='midi_players')
            
            logger.info(f'Seeked to position: {tick}')
        except Exception as e:
            logger.error(f"Error seeking: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('volume')
    def handle_volume(volume_value):
        """Set playback volume (matches frontend expectation)"""
        try:
            volume = int(volume_value) if isinstance(volume_value, (int, str)) else volume_value
            gateway.set_volume(volume)
            emit('volumeUpdate', volume, room='midi_players')
            logger.info(f'Volume set to: {volume}')
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('set_volume')
    def handle_set_volume(data):
        """Set playback volume (alternative API)"""
        try:
            volume = data.get('volume', 100)
            gateway.set_volume(volume)
            emit('volumeUpdate', volume, room='midi_players')
            logger.info(f'Volume set to: {volume}')
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            emit('error', {'message': str(e)})
    
    @socketio.on('get_status')
    def handle_get_status():
        """Get current player status"""
        try:
            status = gateway.get_status()
            emit('player_status', status)
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            emit('error', {'message': str(e)})
    