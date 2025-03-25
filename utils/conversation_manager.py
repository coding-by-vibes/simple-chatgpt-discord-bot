"""
Enhanced Conversation Management Module
This module provides functionality for managing conversations, context, and user interactions.

To enable this feature:
1. Uncomment the entire ConversationManager class below
2. Uncomment the import in bot.py
3. Uncomment the conversation_manager initialization in bot.py
4. Uncomment the command functions in bot.py
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass, asdict
from utils.cache_manager import CacheManager
from collections import defaultdict

@dataclass
class Message:
    """Represents a message in a conversation."""
    role: str
    content: str
    timestamp: str
    metadata: Dict[str, Any]

@dataclass
class Conversation:
    """Represents a conversation with context and metadata."""
    messages: List[Message]
    context: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str

class ConversationManager:
    def __init__(self, settings_dir: str):
        """Initialize the conversation manager.
        
        Args:
            settings_dir: Directory to store conversation data
        """
        self.settings_dir = settings_dir
        self.conversations_dir = os.path.join(settings_dir, "conversations")
        self.logger = logging.getLogger(__name__)
        
        # Create conversations directory
        os.makedirs(self.conversations_dir, exist_ok=True)
        
        # Initialize cache manager
        self.cache_manager = CacheManager(settings_dir)
        
        # Cache TTLs
        self.ACTIVE_CONV_TTL = 3600  # 1 hour for active conversations
        self.CONV_STATS_TTL = 21600  # 6 hours for conversation statistics
    
    def create_conversation(self, conversation_id: str, settings: Optional[Dict[str, Any]] = None) -> Conversation:
        """Create a new conversation.
        
        Args:
            conversation_id: Unique identifier for the conversation
            settings: Optional conversation settings
            
        Returns:
            New conversation object
        """
        # Merge settings with defaults
        settings = settings or {}
        conversation_settings = {**self.default_settings, **settings}
        
        # Create conversation object
        conversation = Conversation(
            messages=[],
            context={},
            metadata={
                "settings": conversation_settings,
                "topic": None,
                "sentiment": None,
                "participants": set()
            },
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # Save conversation
        self._save_conversation(conversation_id, conversation)
        
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            Conversation object if found, None otherwise
        """
        try:
            # Try to get from cache first
            cached_conv = self.cache_manager.get("conversations", conversation_id)
            if cached_conv is not None:
                return self._deserialize_conversation(cached_conv)
            
            # If not in cache, load from disk
            file_path = os.path.join(self.conversations_dir, f"{conversation_id}.json")
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                conversation = self._deserialize_conversation(data)
                
                # Cache the conversation if it's recent
                if (datetime.now() - conversation.updated_at).total_seconds() < 3600:
                    self.cache_manager.set(
                        "conversations",
                        conversation_id,
                        data,
                        ttl=self.ACTIVE_CONV_TTL,
                        cache_type='memory'
                    )
                
                return conversation
                
        except Exception as e:
            self.logger.error(f"Error getting conversation {conversation_id}: {e}")
            return None
    
    def add_message(self, conversation_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add a message to a conversation.
        
        Args:
            conversation_id: Unique identifier for the conversation
            role: Role of the message sender
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conversation = self.get_conversation(conversation_id)
            if not conversation:
                conversation = self.create_conversation(conversation_id)
            
            # Create message
            message = Message(
                role=role,
                content=content,
                timestamp=datetime.now().isoformat(),
                metadata=metadata or {}
            )
            
            # Add message to conversation
            conversation.messages.append(message)
            conversation.updated_at = datetime.now().isoformat()
            
            # Update conversation metadata
            conversation.metadata["participants"].add(role)
            
            # Save conversation
            self._save_conversation(conversation_id, conversation)
            
            return True
        except Exception as e:
            self.logger.error(f"Error adding message to conversation {conversation_id}: {e}")
            return False
    
    def get_conversation_history(self, conversation_id: str, limit: Optional[int] = None) -> List[Message]:
        """Get conversation history.
        
        Args:
            conversation_id: Unique identifier for the conversation
            limit: Optional limit on number of messages to return
            
        Returns:
            List of messages
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        
        messages = conversation.messages
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def update_conversation_settings(self, conversation_id: str, settings: Dict[str, Any]) -> bool:
        """Update conversation settings.
        
        Args:
            conversation_id: Unique identifier for the conversation
            settings: New settings to apply
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conversation = self.get_conversation(conversation_id)
            if not conversation:
                return False
            
            # Update settings
            conversation.metadata["settings"].update(settings)
            conversation.updated_at = datetime.now().isoformat()
            
            # Save conversation
            self._save_conversation(conversation_id, conversation)
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating conversation settings {conversation_id}: {e}")
            return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = os.path.join(self.conversations_dir, f"{conversation_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        except Exception as e:
            self.logger.error(f"Error deleting conversation {conversation_id}: {e}")
            return False
    
    def get_conversation_stats(self, guild_id: str) -> Dict[str, Any]:
        """Get conversation statistics for a guild.
        
        Args:
            guild_id: The Discord guild ID
            
        Returns:
            Dict containing conversation statistics
        """
        try:
            # Try to get from cache first
            cache_key = f"stats_{guild_id}"
            cached_stats = self.cache_manager.get("conversation_stats", cache_key)
            if cached_stats is not None:
                return cached_stats
            
            # If not in cache, compute statistics
            stats = {
                "total_conversations": 0,
                "active_conversations": 0,
                "total_messages": 0,
                "average_length": 0,
                "topics": defaultdict(int),
                "recent_conversations": []
            }
            
            # Process all conversation files for the guild
            conversations = []
            for filename in os.listdir(self.conversations_dir):
                if filename.endswith(f"_{guild_id}.json"):
                    with open(os.path.join(self.conversations_dir, filename), "r") as f:
                        conv_data = json.load(f)
                        conversations.append(conv_data)
                        
                        stats["total_conversations"] += 1
                        stats["total_messages"] += len(conv_data["messages"])
                        
                        # Update topic counts
                        for topic in conv_data.get("topics", []):
                            stats["topics"][topic] += 1
                        
                        # Check if conversation is active (last message within 24 hours)
                        last_message_time = datetime.fromisoformat(conv_data["updated_at"])
                        if (datetime.now() - last_message_time).total_seconds() < 86400:
                            stats["active_conversations"] += 1
            
            # Calculate averages
            if stats["total_conversations"] > 0:
                stats["average_length"] = stats["total_messages"] / stats["total_conversations"]
            
            # Get recent conversations
            recent_convs = sorted(
                conversations,
                key=lambda x: x["updated_at"],
                reverse=True
            )[:5]
            
            stats["recent_conversations"] = [
                {
                    "id": conv["id"],
                    "title": conv["title"],
                    "message_count": len(conv["messages"]),
                    "last_message_time": conv["updated_at"]
                }
                for conv in recent_convs
            ]
            
            # Cache the statistics
            self.cache_manager.set(
                "conversation_stats",
                cache_key,
                stats,
                ttl=self.CONV_STATS_TTL,
                cache_type='disk'
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting conversation stats for guild {guild_id}: {e}")
            return {
                "error": f"Failed to get conversation statistics: {str(e)}"
            }
    
    def _save_conversation(self, conversation_id: str, conversation: Conversation):
        """Save a conversation to disk.
        
        Args:
            conversation_id: Unique identifier for the conversation
            conversation: Conversation object to save
        """
        file_path = os.path.join(self.conversations_dir, f"{conversation_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self._serialize_conversation(conversation), f, indent=2)
    
    def _serialize_conversation(self, conversation: Conversation) -> Dict[str, Any]:
        """Serialize a conversation object to a dictionary.
        
        Args:
            conversation: Conversation object to serialize
            
        Returns:
            Dictionary representation of the conversation
        """
        return {
            "messages": [asdict(msg) for msg in conversation.messages],
            "context": conversation.context,
            "metadata": {
                **conversation.metadata,
                "participants": list(conversation.metadata["participants"])
            },
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at
        }
    
    def _deserialize_conversation(self, data: Dict[str, Any]) -> Conversation:
        """Deserialize a dictionary to a conversation object.
        
        Args:
            data: Dictionary representation of the conversation
            
        Returns:
            Conversation object
        """
        return Conversation(
            messages=[Message(**msg) for msg in data["messages"]],
            context=data["context"],
            metadata={
                **data["metadata"],
                "participants": set(data["metadata"]["participants"])
            },
            created_at=data["created_at"],
            updated_at=data["updated_at"]
        ) 