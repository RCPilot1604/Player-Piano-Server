from flask import current_app
import flask_socketio
import json
import subprocess
import os
import time
from threading import Thread
from datetime import datetime
import logging
from app.utils.instruments import GeneralMidiInstrument
from alsa_midi import SequencerClient, NoteOnEvent, NoteOffEvent, ControlChangeEvent
from ...parsers.midi_parser import MidiParser
from ...parsers.midi_events import MidiEvent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MidiPlayerGateway:
    def __init__(self):
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
        self.socketio = flask_socketio.SocketIO(current_app)
        # For logging MIDI events
        self.midi_log_path = None

    def player_thread_function(self, socketio):
        """Thread function to handle playback logic"""
        client = SequencerClient("Player Piano")
        while True:
            if self.stop_event: 
                self.midi_idx = 0
                socketio.emit('playback_finished', room='midi_players')
                break
            while self.pause_event:
                pass # Do nothing; halt the execution
            if self.midi_idx >= len(self.current_events):
                self.pause_event = True
                self.midi_idx = 0
                socketio.emit('playback_finished', room='midi_players')
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
                socketio.emit('timeUpdate', (event.timestamp / self.total_duration) * 100, room='midi_players')
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
            self.player_thread = Thread(target=self.player_thread_function, args=(self.socketio,))
            self.stop_event = False
            self.pause_event = True
            self.midi_idx = 0
            self.player_thread.start() #start the player thread whenever 
            return True
        except Exception as e:
            logger.error(f"Error parsing MIDI file: {e}")
            self.socketio.emit('error', {'message': f'Failed to parse MIDI file: {str(e)}'})
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
                self.socketio.emit('instruments', instrument_names, room='midi_players')

            return True
        except Exception as e:
            logger.error(f"Error loading song: {e}")
            self.socketio.emit('error', {'message': f'Failed to load song: {str(e)}'})
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
        # This would be called by your ALSA player or timing mechanism
        from flask_socketio import emit
        emit('timeUpdate', position, room='midi_players')
    
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

# Global gateway instance
gateway = MidiPlayerGateway()

# WebSocket Event Handlers
def register_websocket_events(socketio):
    """Register all WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        logger.info('Client connected')
        flask_socketio.join_room('midi_players')
        socketio.emit('connected', {'status': 'Connected to MIDI Player'})
        socketio.emit('player_status', gateway.get_status())
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        logger.info('Client disconnected')
        flask_socketio.leave_room('midi_players')
    
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
    