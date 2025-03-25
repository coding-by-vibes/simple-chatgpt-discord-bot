from typing import Dict, List, Optional, Tuple
import time
from .settings_manager import SettingsManager
import openai
import logging
import os
import json
from datetime import datetime
import asyncio

class ConversationManager:
    def __init__(self, settings_dir: str):
        # Store conversations by channel and user
        self.channel_conversations: Dict[str, List[Dict]] = {}  # Key: f"channel_{channel_id}"
        self.user_conversations: Dict[str, List[Dict]] = {}  # Key: user_id
        self.last_activity: Dict[str, float] = {}  # Key: channel_id or user_id
        self.settings_dir = settings_dir
        self.conversations_dir = os.path.join(settings_dir, "conversations")
        self.settings_manager = SettingsManager(settings_dir)
        self.logger = logging.getLogger(__name__)
        
        # Create conversations directory
        os.makedirs(self.conversations_dir, exist_ok=True)
        
        # Set up OpenAI API key
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
            
        # Initialize cleanup task as None
        self.cleanup_task = None

    async def start_cleanup_task(self):
        """Start the cleanup task. This should be called after the event loop is running."""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_old_conversations())
            self.logger.info("Started conversation cleanup task")

    async def stop_cleanup_task(self):
        """Stop the cleanup task."""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            self.logger.info("Stopped conversation cleanup task")

    async def _cleanup_old_conversations(self):
        """Periodically clean up old conversations."""
        while True:
            try:
                # Clean up every hour
                await asyncio.sleep(3600)
                
                current_time = time.time()
                for key in list(self.last_activity.keys()):
                    # Get conversation settings for the key
                    user_id = key.split('_')[-1] if key.startswith('channel_') else key
                    channel_id = key.split('_')[1] if key.startswith('channel_') else None
                    settings = self.get_conversation_settings(user_id, channel_id)
                    timeout_minutes = settings["timeout_minutes"]
                    
                    # Check if conversation has timed out
                    if current_time - self.last_activity[key] > timeout_minutes * 60:
                        # Clear the conversation
                        self.clear_conversation(user_id, channel_id)
                        self.logger.info(f"Cleaned up old conversation for {key}")
                        
            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying

    def _get_conversation_key(self, user_id: str, channel_id: Optional[str] = None) -> Tuple[str, bool]:
        """Get the conversation key and whether it's a channel conversation.
        
        Args:
            user_id: The Discord user ID
            channel_id: Optional channel ID as string
            
        Returns:
            Tuple[str, bool]: (conversation_key, is_channel_conversation)
        """
        if channel_id is None:
            return user_id, False  # User conversation
        return f"channel_{channel_id}", True  # Channel conversation

    def _save_conversation(self, key: str, is_channel: bool):
        """Save conversation to disk."""
        try:
            conversations = self.channel_conversations if is_channel else self.user_conversations
            if key in conversations:
                file_path = os.path.join(self.conversations_dir, f"{key}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "messages": conversations[key],
                        "last_activity": self.last_activity.get(key, time.time()),
                        "updated_at": datetime.now().isoformat(),
                        "is_channel": is_channel
                    }, f, indent=4)
        except Exception as e:
            self.logger.error(f"Error saving conversation for {key}: {e}")

    def _load_conversation(self, key: str, is_channel: bool):
        """Load conversation from disk."""
        try:
            file_path = os.path.join(self.conversations_dir, f"{key}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    conversations = self.channel_conversations if is_channel else self.user_conversations
                    conversations[key] = data.get("messages", [])
                    self.last_activity[key] = data.get("last_activity", time.time())
        except Exception as e:
            self.logger.error(f"Error loading conversation for {key}: {e}")

    def get_conversation_settings(self, user_id: str, channel_id: Optional[int] = None) -> Dict:
        """Get conversation settings for the user's current persona."""
        settings = self.settings_manager.get_user_settings(user_id)
        current_persona = settings.get("current_persona", "default")
        personas = settings.get("personas", {})
        persona = personas.get(current_persona, personas.get("default", {}))
        
        # Get conversation settings from persona, with defaults
        conv_settings = persona.get("conversation_settings", {})
        return {
            "max_history": conv_settings.get("max_history", 10),
            "timeout_minutes": conv_settings.get("timeout_minutes", 30),
            "include_context": conv_settings.get("include_context", True),
            "model": conv_settings.get("model", "gpt-4o-mini")  # Default to gpt-4o-mini
        }

    def _enforce_conversation_limits(self, key: str, is_channel: bool) -> None:
        """Enforce conversation size limits and clean up if necessary.
        
        Args:
            key: The conversation key
            is_channel: Whether this is a channel conversation
        """
        try:
            conversations = self.channel_conversations if is_channel else self.user_conversations
            if key not in conversations:
                return
                
            # Get conversation settings
            user_id = key.split('_')[-1] if key.startswith('channel_') else key
            channel_id = key.split('_')[1] if key.startswith('channel_') else None
            settings = self.get_conversation_settings(user_id, channel_id)
            max_history = settings["max_history"]
            
            # Check total size of conversation
            total_size = sum(len(msg["content"]) for msg in conversations[key])
            max_total_size = 10000  # Maximum total size in characters
            
            if total_size > max_total_size:
                # Remove oldest messages until we're under the limit
                while total_size > max_total_size and conversations[key]:
                    removed_msg = conversations[key].pop(0)
                    total_size -= len(removed_msg["content"])
                self.logger.info(f"Trimmed conversation {key} to reduce total size")
            
            # Ensure we don't exceed max_history
            if len(conversations[key]) > max_history:
                conversations[key] = conversations[key][-max_history:]
                self.logger.info(f"Trimmed conversation {key} to max_history ({max_history})")
                
        except Exception as e:
            self.logger.error(f"Error enforcing conversation limits for {key}: {e}")

    def add_message(self, user_id: str, role: str, content: str, channel_id: Optional[str] = None) -> bool:
        """Add a message to the conversation history.
        
        Args:
            user_id: The Discord user ID
            role: The role of the message sender
            content: The message content
            channel_id: Optional channel ID as string for channel conversations
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get conversation key and type
            key, is_channel = self._get_conversation_key(user_id, channel_id)
            conversations = self.channel_conversations if is_channel else self.user_conversations
            
            # Load existing conversation if not in memory
            if key not in conversations:
                self._load_conversation(key, is_channel)
            
            if key not in conversations:
                conversations[key] = []
            
            # Add new message
            conversations[key].append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "channel_id": channel_id
            })
            
            # Enforce conversation limits
            self._enforce_conversation_limits(key, is_channel)
            
            # Update last activity timestamp
            self.last_activity[key] = time.time()
            
            # Save to disk
            self._save_conversation(key, is_channel)
            
            return True
        except Exception as e:
            self.logger.error(f"Error adding message to conversation: {e}")
            return False

    def get_conversation(self, user_id: str, channel_id: Optional[int] = None) -> List[Dict]:
        """Get the conversation history for a user or channel."""
        # Get conversation key and type
        key, is_channel = self._get_conversation_key(user_id, channel_id)
        conversations = self.channel_conversations if is_channel else self.user_conversations
        
        # Load conversation if not in memory
        if key not in conversations:
            self._load_conversation(key, is_channel)
            
        if key not in conversations:
            return []
        
        # Get conversation settings for current persona
        settings = self.get_conversation_settings(user_id, channel_id)
        timeout_minutes = settings["timeout_minutes"]
        include_context = settings["include_context"]
        
        # Check if conversation has timed out
        if time.time() - self.last_activity[key] > timeout_minutes * 60:
            conversations[key] = []
            self._save_conversation(key, is_channel)
            return []
        
        # Return conversation history if context is enabled
        return conversations[key] if include_context else []

    def clear_conversation(self, user_id: str, channel_id: Optional[int] = None) -> None:
        """Clear the conversation history for a user or channel."""
        key, is_channel = self._get_conversation_key(user_id, channel_id)
        conversations = self.channel_conversations if is_channel else self.user_conversations
        
        if key in conversations:
            conversations[key] = []
        if key in self.last_activity:
            self.last_activity[key] = time.time()
        self._save_conversation(key, is_channel)

    def is_conversation_active(self, user_id: str, channel_id: Optional[int] = None) -> bool:
        """Check if there is an active conversation for a user or channel."""
        key, is_channel = self._get_conversation_key(user_id, channel_id)
        conversations = self.channel_conversations if is_channel else self.user_conversations
        
        # Load conversation if not in memory
        if key not in conversations:
            self._load_conversation(key, is_channel)
            
        if key not in conversations or not conversations[key]:
            return False
        
        # Get conversation settings for current persona
        settings = self.get_conversation_settings(user_id, channel_id)
        timeout_minutes = settings["timeout_minutes"]
        
        # Check if conversation has timed out
        return time.time() - self.last_activity[key] <= timeout_minutes * 60

    async def generate_response(self, user_id: str, message: str, channel_id: Optional[str] = None) -> str:
        """Generate a response to the user's message.
        
        Args:
            user_id: The Discord user ID
            message: The user's message
            channel_id: Optional channel ID as string for channel conversations
            
        Returns:
            str: The generated response
        """
        try:
            # Get conversation history
            conversation = self.get_conversation(user_id, channel_id)
            
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
            settings = self.get_conversation_settings(user_id, channel_id)
            model = settings["model"]
            
            # Generate response using OpenAI with retries
            max_retries = 3
            retry_delay = 1  # seconds
            
            for attempt in range(max_retries):
                try:
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=messages,
                        max_tokens=1000,
                        temperature=0.7,
                        request_timeout=30  # 30 second timeout
                    )
                    return response.choices[0].message['content']
                    
                except openai.error.RateLimitError as e:
                    if attempt == max_retries - 1:
                        self.logger.error(f"Rate limit exceeded after {max_retries} attempts: {e}")
                        return "I'm currently experiencing high demand. Please try again in a few moments."
                    await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    
                except openai.error.APIError as e:
                    self.logger.error(f"OpenAI API error: {e}")
                    return "I encountered an error with the AI service. Please try again later."
                    
                except openai.error.Timeout as e:
                    self.logger.error(f"OpenAI API timeout: {e}")
                    if attempt == max_retries - 1:
                        return "The request timed out. Please try again."
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    
                except Exception as e:
                    self.logger.error(f"Unexpected error generating response: {e}")
                    return "An unexpected error occurred. Please try again later."
                    
        except Exception as e:
            self.logger.error(f"Error in generate_response: {e}")
            return "I apologize, but I encountered an error while processing your message. Please try again later." 