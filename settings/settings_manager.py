import json
import os
from pathlib import Path
from typing import Dict

class SettingsManager:
    def __init__(self, settings_dir: str = None):
        self.settings_dir = Path(settings_dir) if settings_dir else Path("settings")
        self.servers_dir = self.settings_dir / "servers"
        self.personas_dir = self.settings_dir / "personas"
        self.default_settings_path = self.settings_dir / "default_settings.json"
        
        # Create necessary directories
        self.settings_dir.mkdir(exist_ok=True)
        self.servers_dir.mkdir(exist_ok=True)
        self.personas_dir.mkdir(exist_ok=True)
        
        # Load default settings
        self.default_settings = self._load_json(self.default_settings_path)
        if not self.default_settings:
            self.default_settings = {
                "personas": {
                    "default": {
                        "name": "Default Assistant",
                        "role": "You are a helpful and friendly AI assistant.",
                        "traits": ["helpful", "friendly", "professional"],
                        "style": "neutral"
                    }
                },
                "current_persona": "default",
                "model": "gpt-4o-mini",
                "max_tokens": 2000,
                "temperature": 0.7
            }
            self._save_json(self.default_settings_path, self.default_settings)

    def _load_json(self, file_path):
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"Error loading settings from {file_path}: {e}")
            return None

    def _save_json(self, file_path, data):
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving settings to {file_path}: {e}")
            return False

    def get_server_settings(self, guild_id):
        """Get settings for a specific server, creating default if not exists."""
        server_file = self.servers_dir / f"{guild_id}.json"
        settings = self._load_json(server_file)
        
        if not settings:
            settings = self.default_settings.copy()
            self._save_json(server_file, settings)
        
        return settings

    def update_server_settings(self, guild_id, new_settings):
        """Update settings for a specific server."""
        server_file = self.servers_dir / f"{guild_id}.json"
        current_settings = self.get_server_settings(guild_id)
        
        # Deep merge the settings
        merged_settings = self._deep_merge(current_settings, new_settings)
        
        if self._save_json(server_file, merged_settings):
            return merged_settings
        return None

    def _deep_merge(self, dict1, dict2):
        """Deep merge two dictionaries."""
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get_personality_prompt(self, guild_id):
        """Get the personality prompt for a specific server."""
        settings = self.get_server_settings(guild_id)
        current_persona = settings.get("current_persona", "default")
        personas = settings.get("personas", {})
        persona = personas.get(current_persona, personas.get("default", {}))
        
        prompt_parts = []
        
        # Add role
        if "role" in persona:
            prompt_parts.append(persona["role"])
        
        # Add traits
        if "traits" in persona and persona["traits"]:
            traits = ", ".join(persona["traits"])
            prompt_parts.append(f"You have the following traits: {traits}.")
        
        # Add style
        if "style" in persona and persona["style"] != "neutral":
            prompt_parts.append(f"Your communication style is {persona['style']}.")
        
        return " ".join(prompt_parts)

    def get_available_personas(self, guild_id):
        """Get a list of available personas for a server."""
        settings = self.get_server_settings(guild_id)
        personas = settings.get("personas", {})
        return [(key, persona.get("name", key)) for key, persona in personas.items()]

    def set_current_persona(self, guild_id, persona_id):
        """Set the current persona for a server."""
        settings = self.get_server_settings(guild_id)
        if persona_id in settings.get("personas", {}):
            settings["current_persona"] = persona_id
            self._save_json(self.servers_dir / f"{guild_id}.json", settings)
            return True
        return False

    def add_persona(self, guild_id, persona_id, persona_data):
        """Add a new persona to a server's settings."""
        settings = self.get_server_settings(guild_id)
        if "personas" not in settings:
            settings["personas"] = {}
        
        settings["personas"][persona_id] = persona_data
        return self._save_json(self.servers_dir / f"{guild_id}.json", settings)

    def load_custom_personas(self, guild_id: int) -> Dict:
        """Load custom personas from JSON files in the personas directory and include default personas."""
        custom_personas = {}
        
        try:
            # First, add all default personas
            if "personas" in self.default_settings:
                custom_personas.update(self.default_settings["personas"])
            
            # Get the personas directory for this guild
            guild_personas_dir = self.personas_dir / str(guild_id)
            if not guild_personas_dir.exists():
                guild_personas_dir.mkdir(parents=True)
                return custom_personas

            # Load all JSON files in the personas directory
            for file_path in guild_personas_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        persona_data = json.load(f)
                        # Use the filename (without extension) as the persona ID
                        persona_id = file_path.stem
                        custom_personas[persona_id] = persona_data
                except Exception as e:
                    print(f"Error loading persona file {file_path}: {e}")
                    continue

            return custom_personas
        except Exception as e:
            print(f"Error loading custom personas: {e}")
            return custom_personas 