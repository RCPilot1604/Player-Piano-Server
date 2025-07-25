# WebSocket MIDI gateway package
# Contains the MIDI player gateway functionality migrated from NestJS

from .routes import register_websocket_events

def register_events(socketio):
    """Register WebSocket events with the SocketIO instance"""
    register_websocket_events(socketio)
