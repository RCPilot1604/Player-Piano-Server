from flask import request, jsonify, current_app
from app.api.category import bp
import json
import os
from datetime import datetime

@bp.route('/', methods=['GET'])
def get_categories():
    """Get all categories from database"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            data = json.load(f)
        return jsonify(data.get('categories', [])), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:category_id>', methods=['GET'])
def get_category(category_id):
    """Get a specific category by ID"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        
        # Find category by ID
        for category in categories:
            if category.get('id') == category_id:
                return jsonify(category), 200
        
        return jsonify({'error': 'Category not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/', methods=['POST'])
def create_category():
    """Create a new category"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['name']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        # Check if category with same name already exists
        existing_categories = database.get('categories', [])
        for category in existing_categories:
            if category.get('name', '').lower() == data['name'].lower():
                return jsonify({'error': 'Category with this name already exists'}), 409
        
        # Add metadata
        data['id'] = generate_category_id(existing_categories)
        data['createdAt'] = datetime.utcnow().isoformat()
        data['updatedAt'] = datetime.utcnow().isoformat()
        
        # Add to database
        if 'categories' not in database:
            database['categories'] = []
        
        database['categories'].append(data)
        
        # Save to file
        save_database_to_file(database)
        
        return jsonify(data), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """Update an existing category"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        
        # Find category by ID
        category_index = None
        for i, category in enumerate(categories):
            if category.get('id') == category_id:
                category_index = i
                break
        
        if category_index is not None:
            # Check for duplicate name (excluding current category)
            if 'name' in data:
                for i, category in enumerate(categories):
                    if (i != category_index and 
                        category.get('name', '').lower() == data['name'].lower()):
                        return jsonify({'error': 'Category with this name already exists'}), 409
            
            # Preserve original creation date and ID
            original_created_at = categories[category_index].get('createdAt')
            original_id = categories[category_index].get('id')
            
            # Update category data
            categories[category_index].update(data)
            categories[category_index]['updatedAt'] = datetime.utcnow().isoformat()
            
            # Restore original metadata
            if original_created_at:
                categories[category_index]['createdAt'] = original_created_at
            if original_id:
                categories[category_index]['id'] = original_id
            
            # Save to file
            save_database_to_file(database)
            
            return jsonify(categories[category_index]), 200
        else:
            return jsonify({'error': 'Category not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """Delete a category"""
    try:
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        songs = database.get('songs', [])
        
        # Find and remove category by ID
        deleted_category = None
        for i, category in enumerate(categories):
            if category.get('id') == category_id:
                deleted_category = categories.pop(i)
                break
        
        if deleted_category:
            # Check if any songs use this category
            songs_using_category = [
                song for song in songs 
                if song.get('category') == deleted_category.get('name')
            ]
            
            if songs_using_category:
                return jsonify({
                    'error': 'Cannot delete category. It is being used by songs.',
                    'songs_count': len(songs_using_category)
                }), 409
            
            # Save to file
            save_database_to_file(database)
            return jsonify(deleted_category), 200
        else:
            return jsonify({'error': 'Category not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/<int:category_id>/songs', methods=['GET'])
def get_songs_by_category(category_id):
    """Get all songs in a specific category"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        songs = database.get('songs', [])
        
        # Find category by ID
        category = None
        for cat in categories:
            if cat.get('id') == category_id:
                category = cat
                break
        
        if not category:
            return jsonify({'error': 'Category not found'}), 404
        
        # Find songs in this category
        category_songs = [
            song for song in songs 
            if song.get('category') == category.get('name')
        ]
        
        return jsonify({
            'category': category,
            'songs': category_songs,
            'count': len(category_songs)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/search', methods=['GET'])
def search_categories():
    """Search categories by name"""
    try:
        query = request.args.get('q', '').lower()
        
        if not query:
            return jsonify({'error': 'Search query required'}), 400
        
        # Read current database
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        
        # Filter categories by search query
        filtered_categories = [
            category for category in categories
            if query in category.get('name', '').lower()
        ]
        
        return jsonify(filtered_categories), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/stats', methods=['GET'])
def get_category_stats():
    """Get statistics about categories and their song counts"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        with open(db_path, 'r') as f:
            database = json.load(f)
        
        categories = database.get('categories', [])
        songs = database.get('songs', [])
        
        # Calculate song counts per category
        category_stats = []
        for category in categories:
            song_count = sum(
                1 for song in songs 
                if song.get('category') == category.get('name')
            )
            
            category_stats.append({
                'id': category.get('id'),
                'name': category.get('name'),
                'song_count': song_count,
                'created_at': category.get('createdAt'),
                'updated_at': category.get('updatedAt')
            })
        
        # Sort by song count (descending)
        category_stats.sort(key=lambda x: x['song_count'], reverse=True)
        
        return jsonify({
            'total_categories': len(categories),
            'total_songs': len(songs),
            'category_stats': category_stats
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Helper functions
def save_database_to_file(database):
    """Save database to db.json file"""
    try:
        assets_folder = current_app.config.get('ASSETS_FOLDER')
        db_path = os.path.join(assets_folder, 'db.json')
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        with open(db_path, 'w') as f:
            json.dump(database, f, indent=2)
    except Exception as e:
        print(f"Error saving database: {e}")

def generate_category_id(categories):
    """Generate a unique category ID"""
    if not categories:
        return 1
    
    # Find the highest ID and add 1
    max_id = max([category.get('id', 0) for category in categories], default=0)
    return max_id + 1