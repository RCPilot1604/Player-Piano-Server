import os

class Settings:
    """A class to manage application settings."""
    
    def __init__(self):
        self.settings = {
            'midi_json_file_path': '/tmp/final_data.json',
            'midi_tile_data_file_path': './tmp/midi_tile_data.json',
            'clock_period': 0.02, # 20 ms
            'lowest_note': 21,  # A0
            'highest_note': 108,  # C8
            'activation_duration': 50, # milliseconds
            'deactivation_duration': 75, # milliseconds
            'bounceback_velocity': 127, # Default velocity for bounceback
            'bounce_back_startup_duration': 20, # milliseconds
            'bounce_back_velocity_duration': 10, # milliseconds
            'bounce_back_hold_duration': 0, # milliseconds
            'max_notes': 10
        }
        self.settings['bounce_back_duration'] = (
            self.settings['bounce_back_startup_duration'] + 
            self.settings['bounce_back_velocity_duration'] + 
            self.settings['bounce_back_hold_duration']
        )
        if os.path.exists('./tmp/settings.json'):
            self.load_settings('./tmp/settings.json')
        else:
            self.save_settings('./tmp/settings.json')
    
    def load_settings(self, file_path):
        """Load settings from a JSON file."""
        import json
        try:
            with open(file_path, 'r') as f:
                self.settings = json.load(f)
        except FileNotFoundError:
            print(f"Settings file {file_path} not found.")
    
    def save_settings(self, file_path):
        """Save settings to a JSON file."""
        import json
        dir_path = os.path.dirname(file_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        with open(file_path, 'w') as f:
            json.dump(self.settings, f, indent=2)