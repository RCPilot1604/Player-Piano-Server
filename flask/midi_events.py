"""
MIDI Event definitions and utilities for the Player Piano Server
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class MidiEvent:
    """Represents a single MIDI event for a note"""
    tick: int
    type: str
    velocity: int = 0
    time_ms: float = 0.0
    isBounceBack: bool = False
    track: int = -1

    def to_dict(self) -> Dict[str, Any]:
        return {
            'tick': self.tick,
            'timeMs': self.time_ms,
            'type': self.type,
            'velocity': self.velocity,
            'isBounceBack': self.isBounceBack
        }

@dataclass 
class ConvertedEvent:
    """Represents a converted MIDI event with additional metadata"""
    timestamp: float
    deltaT: float
    note: int
    type: str
    velocity: int = 0
    isBounceBack: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp,
            'deltaT': self.deltaT,
            'note': self.note,
            'type': self.type,
            'velocity': self.velocity,
            'isBounceBack': self.isBounceBack
        }
