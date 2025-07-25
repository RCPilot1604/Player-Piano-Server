"""
MIDI Event definitions and utilities for the Player Piano Server
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class MidiEventType(Enum):
    """MIDI event types"""
    NOTE_ON = "note_on"
    NOTE_OFF = "note_off"
    CONTROL_CHANGE = "control_change"
    PROGRAM_CHANGE = "program_change"
    PITCH_BEND = "pitchwheel"
    TEMPO_CHANGE = "tempo"
    UNKNOWN = "unknown"

@dataclass
class MidiEvent:
    """Represents a MIDI event with timing and note information"""
    tick: int
    channel: int
    type: str
    data: bytes
    time_ms: float = 0.0
    note_number: Optional[int] = None
    velocity: Optional[int] = None
    delta_time: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'tick': self.tick,
            'channel': self.channel,
            'type': self.type,
            'command': self._get_command_name(),
            'data': list(self.data),
            'timeMs': self.time_ms,
            'noteNumber': self.note_number,
            'velocity': self.velocity,
            'deltaTime': self.delta_time
        }
    
    def _get_command_name(self) -> str:
        """Convert MIDI type to human-readable command"""
        command_map = {
            'note_on': 'Note on',
            'note_off': 'Note off',
            'control_change': 'Control Change',
            'program_change': 'Program Change',
            'pitchwheel': 'Pitch Bend',
            'tempo': 'Tempo Change'
        }
        return command_map.get(self.type, self.type.title())
    
    def is_note_event(self) -> bool:
        """Check if this is a note on/off event"""
        return self.type in ['note_on', 'note_off']
    
    def is_note_on(self) -> bool:
        """Check if this is a note on event with velocity > 0"""
        return self.type == 'note_on' and (self.velocity or 0) > 0
    
    def is_note_off(self) -> bool:
        """Check if this is a note off event or note on with velocity 0"""
        return (self.type == 'note_off' or 
                (self.type == 'note_on' and (self.velocity or 0) == 0))

def midi_note_to_name(note_number: int) -> str:
    """Convert MIDI note number to note name (e.g., 60 -> C4)"""
    if not isinstance(note_number, int) or note_number < 0 or note_number > 127:
        return "Unknown"
    
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 
                  'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (note_number // 12) - 1
    note = note_names[note_number % 12]
    return f"{note}{octave}"

def note_name_to_midi(note_name: str) -> Optional[int]:
    """Convert note name to MIDI note number (e.g., C4 -> 60)"""
    try:
        note_names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5,
                      'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
        
        # Parse note name (e.g., "C4", "F#3")
        if len(note_name) < 2:
            return None
        
        if '#' in note_name:
            note = note_name[:-1]
            octave = int(note_name[-1])
        else:
            note = note_name[:-1]
            octave = int(note_name[-1])
        
        if note not in note_names:
            return None
        
        midi_number = (octave + 1) * 12 + note_names[note]
        return midi_number if 0 <= midi_number <= 127 else None
    
    except (ValueError, IndexError):
        return None
