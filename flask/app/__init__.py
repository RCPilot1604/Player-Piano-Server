# Create flask/app/__init__.py
import os
from dotenv import load_dotenv
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

load_dotenv()

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Additional configurations
    app.config['ASSETS_FOLDER'] = os.path.join(os.path.abspath(os.curdir), 'assets')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Load database configuration
    load_database(app)
    
    # Initialize extensions
    CORS(app, cors_allowed_origins="*")
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Register blueprints (equivalent to NestJS modules)
    from app.api.crud import bp as crud_bp
    from app.api.category import bp as categories_bp
    from app.api.player import bp as player_bp
    from app.websocket.midi_gateway import register_events
    
    app.register_blueprint(crud_bp, url_prefix='/api/crud')
    app.register_blueprint(categories_bp, url_prefix='/api/categories')
    app.register_blueprint(player_bp, url_prefix='/api/player')

    # Register WebSocket events
    register_events(socketio)
    
    return app

def load_database(app):
    """Load db.json data equivalent to your NestJS assets/db.json"""
    import json
    
    db_path = os.path.join(app.config['ASSETS_FOLDER'], 'db.json')
    if os.path.exists(db_path):
        with open(db_path, 'r') as f:
            app.config['DATABASE'] = json.load(f)
    else:
        app.config['DATABASE'] = {'songs': [], 'categories': []}