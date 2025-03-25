import json
from pathlib import Path
from typing import Dict, Optional, List
import time
from datetime import datetime
import os

class UserManager:
    def __init__(self, settings_dir: Path):
        self.settings_dir = settings_dir
        self.bespoke_dir = os.path.join(settings_dir, "personas", "bespoke")
        self.user_preferences_file = os.path.join(settings_dir, "user_preferences.json")
        self.user_history_dir = os.path.join(settings_dir, "user_history")
        self.user_preferences = self.load_user_preferences()
        
        # Create necessary directories
        os.makedirs(self.bespoke_dir, exist_ok=True)
        os.makedirs(self.user_history_dir, exist_ok=True)
    
    def load_user_preferences(self):
        """Load user preferences from file."""
        if os.path.exists(self.user_preferences_file):
            with open(self.user_preferences_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_user_preferences(self):
        """Save user preferences to file."""
        with open(self.user_preferences_file, 'w') as f:
            json.dump(self.user_preferences, f, indent=4)
    
    def get_user_history_file(self, user_id: str) -> str:
        """Get the path to a user's history file."""
        return os.path.join(self.user_history_dir, f"{user_id}.json")
    
    def get_or_create_user_history(self, user_id: str) -> Dict:
        """Get existing user history or create a new one."""
        history_file = self.get_user_history_file(user_id)
        
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                return json.load(f)
        
        # Create new user history
        history = {
            "user_id": user_id,
            "interaction_history": [],
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "settings": {
                "max_history": 15,
                "timeout_minutes": 60,
                "include_context": True
            }
        }
        
        # Save the new history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=4)
        
        return history
    
    def update_user_history(self, user_id: str, interaction_data: Dict):
        """Update a user's history with new interaction data."""
        history = self.get_or_create_user_history(user_id)
        
        # Add new interaction to history
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "data": interaction_data
        }
        history["interaction_history"].append(interaction)
        
        # Update last_updated timestamp
        history["last_updated"] = datetime.now().isoformat()
        
        # Save updated history
        history_file = self.get_user_history_file(user_id)
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=4)
    
    def get_user_history(self, user_id: str, max_history: int = None) -> List[Dict]:
        """Get a user's interaction history."""
        history = self.get_or_create_user_history(user_id)
        interactions = history.get("interaction_history", [])
        
        if max_history:
            return interactions[-max_history:]
        return interactions
    
    def get_or_create_bespoke_persona(self, user_id: str) -> Dict:
        """Get existing bespoke persona or create a new one with default settings."""
        persona_file = os.path.join(self.bespoke_dir, f"{user_id}.json")
        
        # Load default settings
        default_settings = self.load_default_settings()
        default_assistant = default_settings.get("personas", {}).get("default", {})
        
        if os.path.exists(persona_file):
            with open(persona_file, 'r') as f:
                return json.load(f)
        
        # Create new bespoke persona with default settings
        persona = {
            "name": f"Bespoke Persona for {user_id}",
            "role": default_assistant.get("role", "A personalized AI assistant"),
            "traits": default_assistant.get("traits", []),
            "style": "adaptive",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        
        # Save the new persona
        with open(persona_file, 'w') as f:
            json.dump(persona, f, indent=4)
        
        return persona
    
    def load_default_settings(self) -> Dict:
        """Load default settings from default_settings.json."""
        default_settings_file = os.path.join(self.settings_dir, "default_settings.json")
        if os.path.exists(default_settings_file):
            with open(default_settings_file, 'r') as f:
                return json.load(f)
        return {}
    
    def get_bespoke_persona(self, user_id: str) -> Dict:
        """Get a user's bespoke persona, creating it if it doesn't exist."""
        return self.get_or_create_bespoke_persona(user_id)
    
    def update_bespoke_persona(self, user_id: str, interaction_data: Dict):
        """Update a user's bespoke persona with new interaction data."""
        persona = self.get_bespoke_persona(user_id)
        
        # Add new interaction to history
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "data": interaction_data
        }
        persona["interaction_history"].append(interaction)
        
        # Update last_updated timestamp
        persona["last_updated"] = datetime.now().isoformat()
        
        # Save updated persona
        persona_file = os.path.join(self.bespoke_dir, f"{user_id}.json")
        with open(persona_file, 'w') as f:
            json.dump(persona, f, indent=4)
    
    def get_user_preferred_persona(self, user_id: str) -> str:
        """Get a user's preferred persona."""
        return self.user_preferences.get(user_id, {}).get("preferred_persona")
    
    def set_user_preferred_persona(self, user_id: str, persona: str):
        """Set a user's preferred persona."""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {}
        self.user_preferences[user_id]["preferred_persona"] = persona
        self.save_user_preferences()
    
    def get_user_interaction_stats(self, user_id: str) -> Dict:
        """Get statistics about a user's interactions."""
        history = self.get_or_create_user_history(user_id)
        persona = self.get_or_create_bespoke_persona(user_id)
        
        return {
            "total_interactions": len(history.get("interaction_history", [])),
            "created_at": history.get("created_at"),
            "last_updated": history.get("last_updated"),
            "preferred_persona": self.get_user_preferred_persona(user_id),
            "persona_name": persona.get("name"),
            "persona_style": persona.get("style")
        }
    
    def update_user_history_setting(self, user_id: str, setting: str, value: any) -> None:
        """Update a specific setting in the user's history.
        
        Args:
            user_id: The Discord user ID
            setting: The setting to update (e.g., "max_history")
            value: The new value for the setting
        """
        try:
            # Get the user's history file path
            history_file = os.path.join(self.settings_dir, f"user_{user_id}_history.json")
            
            # Load existing history or create new
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = {
                    "interactions": [],
                    "settings": {
                        "max_history": 5,  # Default value
                        "created_at": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat()
                    }
                }
            
            # Update the setting
            if "settings" not in history:
                history["settings"] = {}
            
            history["settings"][setting] = value
            history["settings"]["last_updated"] = datetime.now().isoformat()
            
            # Save the updated history
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error updating user history setting: {e}")
            raise 