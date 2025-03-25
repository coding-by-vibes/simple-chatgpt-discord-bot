from typing import Dict, List, Optional
import time
from .settings_manager import SettingsManager
import openai

class ConversationManager:
    def __init__(self, settings_dir: str):
        self.conversations: Dict[int, List[Dict]] = {}
        self.last_activity: Dict[int, float] = {}
        self.settings_dir = settings_dir
        self.settings_manager = SettingsManager(settings_dir)

    def get_conversation_settings(self, guild_id: int) -> Dict:
        """Get conversation settings for the current persona in the guild."""
        settings = self.settings_manager.get_server_settings(guild_id)
        current_persona = settings.get("current_persona", "default")
        personas = settings.get("personas", {})
        persona = personas.get(current_persona, personas.get("default", {}))
        
        # Get conversation settings from persona, with defaults
        conv_settings = persona.get("conversation_settings", {})
        return {
            "max_history": conv_settings.get("max_history", 10),
            "timeout_minutes": conv_settings.get("timeout_minutes", 30),
            "include_context": conv_settings.get("include_context", True)
        }

    def add_message(self, guild_id: int, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        if guild_id not in self.conversations:
            self.conversations[guild_id] = []
        
        # Get conversation settings for current persona
        settings = self.get_conversation_settings(guild_id)
        max_history = settings["max_history"]
        
        # Add new message
        self.conversations[guild_id].append({
            "role": role,
            "content": content
        })
        
        # Trim history if it exceeds max_history
        if len(self.conversations[guild_id]) > max_history:
            self.conversations[guild_id] = self.conversations[guild_id][-max_history:]
        
        # Update last activity timestamp
        self.last_activity[guild_id] = time.time()

    def get_conversation(self, guild_id: int) -> List[Dict]:
        """Get the conversation history for a guild."""
        if guild_id not in self.conversations:
            return []
        
        # Get conversation settings for current persona
        settings = self.get_conversation_settings(guild_id)
        timeout_minutes = settings["timeout_minutes"]
        include_context = settings["include_context"]
        
        # Check if conversation has timed out
        if time.time() - self.last_activity[guild_id] > timeout_minutes * 60:
            self.conversations[guild_id] = []
            return []
        
        # Return conversation history if context is enabled
        return self.conversations[guild_id] if include_context else []

    def clear_conversation(self, guild_id: int) -> None:
        """Clear the conversation history for a guild."""
        if guild_id in self.conversations:
            self.conversations[guild_id] = []
        if guild_id in self.last_activity:
            self.last_activity[guild_id] = time.time()

    def is_conversation_active(self, guild_id: int) -> bool:
        """Check if there is an active conversation for a guild."""
        if guild_id not in self.conversations or not self.conversations[guild_id]:
            return False
        
        # Get conversation settings for current persona
        settings = self.get_conversation_settings(guild_id)
        timeout_minutes = settings["timeout_minutes"]
        
        # Check if conversation has timed out
        return time.time() - self.last_activity[guild_id] <= timeout_minutes * 60

    async def generate_response(self, guild_id: int, user_id: str, message: str) -> str:
        """Generate a response to the user's message.
        
        Args:
            guild_id: The Discord guild ID
            user_id: The Discord user ID
            message: The user's message
            
        Returns:
            str: The generated response
        """
        # Get conversation history
        conversation = self.get_conversation(guild_id)
        
        # Prepare messages for OpenAI
        messages = []
        for msg in conversation:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Add the current message
        messages.append({
            "role": "user",
            "content": message
        })
        
        # Get conversation settings
        settings = self.get_conversation_settings(guild_id)
        
        # Generate response using OpenAI
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message['content']
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return "I apologize, but I encountered an error while generating a response. Please try again later." 