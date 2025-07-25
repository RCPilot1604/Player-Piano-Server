import mido
import json
from typing import List, Dict, Any, Optional
import time
from .midi_events import MidiEvent, MidiEventType, midi_note_to_name

class MidiParser:
    def __init__(self, midi_file: str):
        self.mid = mido.MidiFile(midi_file)
        self.ticks_per_beat = self.mid.ticks_per_beat
        self.tempo = 500000  # Default tempo (120 BPM)
        self.events = self._parse_to_events()
        self.duration = self._calculate_duration()
    
    def _parse_to_events(self) -> List[MidiEvent]:
        """Parse MIDI file into MidiEvent objects"""
        events = []
        
        for track_idx, track in enumerate(self.mid.tracks):
            current_tick = 0
            current_tempo = self.tempo
            
            for msg in track:
                current_tick += msg.time
                
                if not msg.is_meta:
                    # Handle note events
                    note_number = getattr(msg, 'note', None)
                    velocity = getattr(msg, 'velocity', None)
                    
                    event = MidiEvent(
                        tick=current_tick,
                        channel=getattr(msg, 'channel', 0),
                        type=msg.type,
                        data=msg.bytes(),
                        note_number=note_number,
                        velocity=velocity
                    )
                    
                    # Calculate time in milliseconds
                    event.time_ms = self._ticks_to_milliseconds(current_tick, current_tempo)
                    
                    events.append(event)
                
                # Handle tempo changes for timing calculations
                elif msg.type == 'set_tempo':
                    current_tempo = msg.tempo
                    self.tempo = current_tempo  # Update global tempo
                    
                    tempo_event = MidiEvent(
                        tick=current_tick,
                        channel=-1,  # Special marker for tempo
                        type='tempo',
                        data=msg.tempo.to_bytes(4, 'big')
                    )
                    
                    tempo_event.time_ms = self._ticks_to_milliseconds(current_tick, current_tempo)
                    events.append(tempo_event)
        
        return sorted(events, key=lambda x: x.tick)
    
    def _ticks_to_milliseconds(self, ticks: int, tempo: int = None) -> float:
        """Convert MIDI ticks to milliseconds"""
        if tempo is None:
            tempo = self.tempo
        
        # Calculate time per tick in seconds
        seconds_per_beat = tempo / 1_000_000  # Tempo is in microseconds per beat
        seconds_per_tick = seconds_per_beat / self.ticks_per_beat
        
        return ticks * seconds_per_tick * 1000  # Convert to milliseconds
    
    def _calculate_duration(self) -> float:
        """Calculate total duration of MIDI file in seconds"""
        if not self.events:
            return 0.0
        
        last_event = max(self.events, key=lambda x: x.time_ms)
        return last_event.time_ms / 1000.0  # Convert to seconds
    
    def get_note_events(self) -> List[MidiEvent]:
        """Get only note on/off events"""
        return [
            event for event in self.events 
            if event.type in ['note_on', 'note_off']
        ]
    
    def get_playback_events(self) -> List[Dict[str, Any]]:
        """Get events formatted for WebSocket playback"""
        note_events = self.get_note_events()
        return [event.to_dict() for event in note_events]
    
    def export_for_alsa(self) -> Dict[str, Any]:
        """Export parsed data in format suitable for ALSA player"""
        return {
            'ticks_per_beat': self.ticks_per_beat,
            'tempo': self.tempo,
            'duration': self.duration,
            'events': [
                {
                    'tick': event.tick,
                    'channel': event.channel,
                    'type': event.type,
                    'data': list(event.data),
                    'time_ms': event.time_ms,
                    'note_number': event.note_number,
                    'velocity': event.velocity
                }
                for event in self.events
            ]
        }
    
    def export_to_json(self, output_file: str) -> bool:
        """Export parsed MIDI data to JSON file"""
        try:
            data = {
                'metadata': {
                    'ticks_per_beat': self.ticks_per_beat,
                    'tempo': self.tempo,
                    'duration': self.duration,
                    'total_events': len(self.events),
                    'note_events': len(self.get_note_events())
                },
                'events': [event.to_dict() for event in self.events]
            }
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error exporting to JSON: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the MIDI file"""
        note_events = self.get_note_events()
        
        # Count notes by channel
        channels = {}
        note_range = {'min': 127, 'max': 0}
        
        for event in note_events:
            if event.type == 'note_on' and event.velocity > 0:
                channel = event.channel
                channels[channel] = channels.get(channel, 0) + 1
                
                if event.note_number:
                    note_range['min'] = min(note_range['min'], event.note_number)
                    note_range['max'] = max(note_range['max'], event.note_number)
        
        return {
            'duration_seconds': self.duration,
            'total_events': len(self.events),
            'note_events': len(note_events),
            'channels_used': list(channels.keys()),
            'notes_per_channel': channels,
            'note_range': note_range,
            'tempo_bpm': 60_000_000 / self.tempo,
            'ticks_per_beat': self.ticks_per_beat
        }
