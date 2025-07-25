# WebSocket package initialization
# Contains MIDI gateway and WebSocket event handlers

from .midi_gateway import register_events

__all__ = ['register_events']
