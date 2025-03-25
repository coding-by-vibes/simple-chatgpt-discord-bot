import json
import os
from typing import Dict, Optional, List
from datetime import datetime
import logging

class UserManager:
    def __init__(self, settings_dir: str):
        """Initialize the user manager.
        
        Args:
            settings_dir: Directory to store user data
        """
        self.settings_dir = settings_dir
        self.users_dir = os.path.join(settings_dir, "users")
        self.logger = logging.getLogger(__name__)
        
        # Create necessary directories
        os.makedirs(self.users_dir, exist_ok=True)
        
    def get_user_data(self, user_id: str) -> Dict:
        """Get user data from file."""
        try:
            user_file = os.path.join(self.users_dir, f"{user_id}.json")
            if os.path.exists(user_file):
                with open(user_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return self._create_default_user_data()
        except Exception as e:
            self.logger.error(f"Error getting user data: {e}")
            return self._create_default_user_data()
            
    def save_user_data(self, user_id: str, data: Dict) -> bool:
        """Save user data to file."""
        try:
            user_file = os.path.join(self.users_dir, f"{user_id}.json")
            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Error saving user data: {e}")
            return False
            
    def _create_default_user_data(self) -> Dict:
        """Create default user data structure."""
        return {
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "settings": {
                "preferred_persona": "default",
                "max_history": 10,
                "auto_summarize": False,
                "notifications": True
            },
            "personas": [],
            "bespoke_persona": None,
            "interaction_history": [],
            "preferences": {}
        }
        
    def update_user_setting(self, user_id: str, setting: str, value: any) -> bool:
        """Update a specific user setting."""
        try:
            user_data = self.get_user_data(user_id)
            user_data["settings"][setting] = value
            return self.save_user_data(user_id, user_data)
        except Exception as e:
            self.logger.error(f"Error updating user setting: {e}")
            return False
            
    def get_user_setting(self, user_id: str, setting: str) -> Optional[any]:
        """Get a specific user setting."""
        try:
            user_data = self.get_user_data(user_id)
            return user_data["settings"].get(setting)
        except Exception as e:
            self.logger.error(f"Error getting user setting: {e}")
            return None
            
    def add_persona(self, user_id: str, persona_data: Dict) -> bool:
        """Add a persona to user's available personas."""
        try:
            user_data = self.get_user_data(user_id)
            user_data["personas"].append(persona_data)
            return self.save_user_data(user_id, user_data)
        except Exception as e:
            self.logger.error(f"Error adding persona: {e}")
            return False
            
    def get_personas(self, user_id: str) -> List[Dict]:
        """Get all personas available to a user."""
        try:
            user_data = self.get_user_data(user_id)
            return user_data.get("personas", [])
        except Exception as e:
            self.logger.error(f"Error getting personas: {e}")
            return []
            
    def set_bespoke_persona(self, user_id: str, persona_data: Dict) -> bool:
        """Set or update a user's bespoke persona."""
        try:
            user_data = self.get_user_data(user_id)
            user_data["bespoke_persona"] = persona_data
            return self.save_user_data(user_id, user_data)
        except Exception as e:
            self.logger.error(f"Error setting bespoke persona: {e}")
            return False
            
    def get_bespoke_persona(self, user_id: str) -> Optional[Dict]:
        """Get a user's bespoke persona if it exists."""
        try:
            user_data = self.get_user_data(user_id)
            return user_data.get("bespoke_persona")
        except Exception as e:
            self.logger.error(f"Error getting bespoke persona: {e}")
            return None
            
    def update_last_active(self, user_id: str) -> bool:
        """Update user's last active timestamp."""
        try:
            user_data = self.get_user_data(user_id)
            user_data["last_active"] = datetime.now().isoformat()
            return self.save_user_data(user_id, user_data)
        except Exception as e:
            self.logger.error(f"Error updating last active: {e}")
            return False
            
    def add_interaction(self, user_id: str, interaction_data: Dict) -> bool:
        """Add an interaction to user's history."""
        try:
            user_data = self.get_user_data(user_id)
            user_data["interaction_history"].append({
                **interaction_data,
                "timestamp": datetime.now().isoformat()
            })
            return self.save_user_data(user_id, user_data)
        except Exception as e:
            self.logger.error(f"Error adding interaction: {e}")
            return False
            
    def get_interaction_history(self, user_id: str, limit: int = None) -> List[Dict]:
        """Get user's interaction history."""
        try:
            user_data = self.get_user_data(user_id)
            history = user_data.get("interaction_history", [])
            if limit:
                return history[-limit:]
            return history
        except Exception as e:
            self.logger.error(f"Error getting interaction history: {e}")
            return []

    def create_bespoke_persona(self, user_id: str) -> Dict:
        """Create a new bespoke persona for a user."""
        try:
            persona_data = {
                "name": f"Bespoke_{user_id}",
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "interactions": 0,
                "preferences": {},
                "learning_data": {}
            }
            
            if self.set_bespoke_persona(user_id, persona_data):
                return persona_data
            return None
        except Exception as e:
            self.logger.error(f"Error creating bespoke persona: {e}")
            return None

    def get_user_interaction_stats(self, user_id: str) -> Dict:
        """Get statistics about a user's interactions."""
        try:
            user_data = self.get_user_data(user_id)
            bespoke = user_data.get("bespoke_persona", {})
            
            return {
                "total_interactions": len(user_data.get("interaction_history", [])),
                "created_at": user_data.get("created_at"),
                "last_updated": user_data.get("last_active"),
                "preferred_persona": user_data["settings"].get("preferred_persona"),
                "bespoke_interactions": bespoke.get("interactions", 0) if bespoke else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting user interaction stats: {e}")
            return None

    def update_user_history_setting(self, user_id: str, setting: str, value: any) -> bool:
        """Update a user's history-related setting."""
        return self.update_user_setting(user_id, setting, value)

    async def get_available_personas(self, user_id: str) -> List[Dict]:
        """Get all personas available to a user, including bespoke."""
        try:
            user_data = self.get_user_data(user_id)
            personas = user_data.get("personas", [])
            
            # Add bespoke persona if it exists
            bespoke = user_data.get("bespoke_persona")
            if bespoke:
                personas.append(bespoke)
                
            return personas
        except Exception as e:
            self.logger.error(f"Error getting available personas: {e}")
            return []

    def set_user_preferred_persona(self, user_id: str, persona_name: str) -> bool:
        """Set a user's preferred persona."""
        return self.update_user_setting(user_id, "preferred_persona", persona_name) 