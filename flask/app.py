#!/usr/bin/env python3
"""
Flask Application Entry Point for Player Piano Server
Migrated from NestJS to Flask for better MIDI timing control with ALSA
"""

import os
import sys
from app import create_app, socketio

def main():
    """Main application entry point"""
    
    # Create Flask app using application factory
    app = create_app()
    
    # Get configuration from environment
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print("=" * 60)
    print("🎹 PLAYER PIANO SERVER - FLASK EDITION")
    print("=" * 60)
    print(f"🌐 Server starting on: http://{host}:{port}")
    print(f"🔌 WebSocket endpoint: ws://{host}:{port}/socket.io/")
    print(f"🐛 Debug mode: {'ON' if debug else 'OFF'}")
    print("=" * 60)
    print("📋 Available Endpoints:")
    print("   • REST API:")
    print(f"     - Songs (CRUD): http://{host}:{port}/api/crud")
    print(f"     - Categories:   http://{host}:{port}/api/categories") 
    print(f"     - Player Info:  http://{host}:{port}/api/player")
    print("   • WebSocket Events:")
    print("     - loadMidi, play, pause, volume, seek")
    print("     - Connected to Angular frontend")
    print("=" * 60)
    print("🎯 Frontend Connection:")
    print("   Update Angular environment files to:")
    print(f"   wsUrl: 'ws://{host}:{port}'")
    print(f"   httpApi: 'http://{host}:{port}'")
    print("=" * 60)
    
    try:
        # Start the server with SocketIO support
        socketio.run(
            app,
            host=host,
            port=port,
            debug=debug,
            allow_unsafe_werkzeug=True  # For development only
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
