import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import re
from collections import defaultdict

class ConversationEnhancer:
    def __init__(self, settings_dir: str):
        """Initialize the conversation enhancer.
        
        Args:
            settings_dir: Directory to store conversation data
        """
        self.settings_dir = settings_dir
        self.conversations_dir = os.path.join(settings_dir, "conversations")
        self.summaries_dir = os.path.join(settings_dir, "summaries")
        self.topics_dir = os.path.join(settings_dir, "topics")
        
        # Create necessary directories
        os.makedirs(self.conversations_dir, exist_ok=True)
        os.makedirs(self.summaries_dir, exist_ok=True)
        os.makedirs(self.topics_dir, exist_ok=True)
        
        # Initialize topic tracking
        self.topic_patterns = {
            "code": r"(programming|code|function|class|method|api|bug|debug|error)",
            "math": r"(calculation|equation|formula|math|number|statistics)",
            "language": r"(grammar|sentence|word|language|translation|dictionary)",
            "general": r"(what|how|why|when|where|who|explain|describe|tell)"
        }
    
    def save_conversation(self, guild_id: str, messages: List[Dict[str, str]]) -> str:
        """Save a conversation with metadata.
        
        Args:
            guild_id: The Discord guild ID
            messages: List of message dictionaries
            
        Returns:
            str: Conversation ID
        """
        # Generate conversation ID
        conversation_id = f"CONV_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{guild_id}"
        
        # Prepare conversation data
        conversation_data = {
            "conversation_id": conversation_id,
            "guild_id": guild_id,
            "timestamp": datetime.now().isoformat(),
            "message_count": len(messages),
            "messages": messages,
            "topics": self._detect_topics(messages),
            "metadata": self._generate_metadata(messages)
        }
        
        # Save conversation
        conv_file = os.path.join(self.conversations_dir, f"{conversation_id}.json")
        with open(conv_file, "w") as f:
            json.dump(conversation_data, f, indent=2)
        
        return conversation_id
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a conversation by ID.
        
        Args:
            conversation_id: The ID of the conversation to retrieve
            
        Returns:
            Optional[Dict]: Conversation data if found, None otherwise
        """
        conv_file = os.path.join(self.conversations_dir, f"{conversation_id}.json")
        if os.path.exists(conv_file):
            with open(conv_file, "r") as f:
                return json.load(f)
        return None
    
    def _detect_topics(self, messages: List[Dict[str, str]]) -> List[str]:
        """Detect topics in conversation messages.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List[str]: List of detected topics
        """
        topics = set()
        text = " ".join(msg["content"].lower() for msg in messages)
        
        for topic, pattern in self.topic_patterns.items():
            if re.search(pattern, text):
                topics.add(topic)
        
        return list(topics)
    
    def _generate_metadata(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Generate metadata for a conversation.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Dict containing conversation metadata
        """
        metadata = {
            "total_messages": len(messages),
            "user_messages": sum(1 for msg in messages if msg["role"] == "user"),
            "bot_messages": sum(1 for msg in messages if msg["role"] == "assistant"),
            "has_code": any("```" in msg["content"] for msg in messages),
            "average_message_length": sum(len(msg["content"]) for msg in messages) / len(messages) if messages else 0,
            "duration": self._calculate_duration(messages)
        }
        
        return metadata
    
    def _calculate_duration(self, messages: List[Dict[str, str]]) -> float:
        """Calculate the duration of a conversation in minutes.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            float: Duration in minutes
        """
        if not messages:
            return 0.0
        
        # Extract timestamps from messages if available
        timestamps = []
        for msg in messages:
            if "timestamp" in msg:
                try:
                    timestamps.append(datetime.fromisoformat(msg["timestamp"]))
                except ValueError:
                    continue
        
        if len(timestamps) < 2:
            return 0.0
        
        # Calculate duration between first and last message
        duration = (max(timestamps) - min(timestamps)).total_seconds() / 60
        return round(duration, 2)
    
    def generate_summary(self, conversation_id: str, summary_type: str = "regular") -> Optional[Dict[str, Any]]:
        """Generate a summary of a conversation.
        
        Args:
            conversation_id: The ID of the conversation to summarize
            summary_type: Type of summary to generate ("brief", "regular", "detailed")
            
        Returns:
            Optional[Dict]: Summary data if successful, None otherwise
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return None
        
        # Prepare summary data
        summary_data = {
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "summary_type": summary_type,
            "topics": conversation["topics"],
            "metadata": conversation["metadata"],
            "key_points": self._extract_key_points(conversation["messages"], summary_type),
            "action_items": self._extract_action_items(conversation["messages"]),
            "decisions": self._extract_decisions(conversation["messages"])
        }
        
        # Save summary
        summary_file = os.path.join(self.summaries_dir, f"{conversation_id}_summary.json")
        with open(summary_file, "w") as f:
            json.dump(summary_data, f, indent=2)
        
        return summary_data
    
    def _extract_key_points(self, messages: List[Dict[str, str]], summary_type: str) -> List[str]:
        """Extract key points from conversation messages.
        
        Args:
            messages: List of message dictionaries
            summary_type: Type of summary to generate
            
        Returns:
            List[str]: List of key points
        """
        key_points = []
        
        # Extract code blocks
        code_blocks = []
        for msg in messages:
            code_matches = re.findall(r"```(?:\w+)?\n(.*?)\n```", msg["content"], re.DOTALL)
            code_blocks.extend(code_matches)
        
        if code_blocks:
            key_points.append(f"Code snippets: {len(code_blocks)} blocks")
        
        # Extract important information based on summary type
        if summary_type == "brief":
            # Just count messages and topics
            key_points.append(f"Total messages: {len(messages)}")
            key_points.append(f"Topics discussed: {', '.join(self._detect_topics(messages))}")
        else:
            # Extract more detailed points
            for msg in messages:
                if msg["role"] == "assistant":
                    # Look for bullet points or numbered lists
                    points = re.findall(r"[-•*]\s*(.*?)(?:\n|$)", msg["content"])
                    key_points.extend(points)
        
        return key_points[:5] if summary_type == "brief" else key_points
    
    def _extract_action_items(self, messages: List[Dict[str, str]]) -> List[str]:
        """Extract action items from conversation messages.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List[str]: List of action items
        """
        action_items = []
        action_patterns = [
            r"(?:need to|should|must|will|going to)\s+(.*?)(?:\n|$)",
            r"(?:TODO|FIXME|NOTE):\s*(.*?)(?:\n|$)",
            r"(?:action item|task):\s*(.*?)(?:\n|$)"
        ]
        
        for msg in messages:
            for pattern in action_patterns:
                matches = re.findall(pattern, msg["content"], re.IGNORECASE)
                action_items.extend(matches)
        
        return action_items
    
    def _extract_decisions(self, messages: List[Dict[str, str]]) -> List[str]:
        """Extract decisions made in the conversation.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            List[str]: List of decisions
        """
        decisions = []
        decision_patterns = [
            r"(?:decided|agreed|concluded|determined)\s+(?:to|that)\s+(.*?)(?:\n|$)",
            r"(?:decision|conclusion):\s*(.*?)(?:\n|$)"
        ]
        
        for msg in messages:
            for pattern in decision_patterns:
                matches = re.findall(pattern, msg["content"], re.IGNORECASE)
                decisions.extend(matches)
        
        return decisions
    
    def get_conversation_stats(self, guild_id: str) -> Dict[str, Any]:
        """Get statistics about conversations in a guild.
        
        Args:
            guild_id: The Discord guild ID
            
        Returns:
            Dict containing conversation statistics
        """
        stats = {
            "total_conversations": 0,
            "conversations_by_topic": defaultdict(int),
            "average_duration": 0,
            "total_messages": 0,
            "recent_conversations": []
        }
        
        # Process all conversation files
        for filename in os.listdir(self.conversations_dir):
            if filename.startswith(f"CONV_") and filename.endswith(f"_{guild_id}.json"):
                with open(os.path.join(self.conversations_dir, filename), "r") as f:
                    conv_data = json.load(f)
                    
                    stats["total_conversations"] += 1
                    stats["total_messages"] += conv_data["message_count"]
                    
                    # Count by topic
                    for topic in conv_data["topics"]:
                        stats["conversations_by_topic"][topic] += 1
                    
                    # Add duration
                    if "metadata" in conv_data and "duration" in conv_data["metadata"]:
                        stats["average_duration"] += conv_data["metadata"]["duration"]
                    
                    # Add to recent conversations
                    stats["recent_conversations"].append({
                        "id": conv_data["conversation_id"],
                        "timestamp": conv_data["timestamp"],
                        "message_count": conv_data["message_count"],
                        "topics": conv_data["topics"]
                    })
        
        # Calculate averages
        if stats["total_conversations"] > 0:
            stats["average_duration"] /= stats["total_conversations"]
        
        # Sort recent conversations
        stats["recent_conversations"].sort(key=lambda x: x["timestamp"], reverse=True)
        stats["recent_conversations"] = stats["recent_conversations"][:5]  # Keep only last 5
        
        return stats
    
    def get_topic_history(self, guild_id: str, topic: str) -> List[Dict[str, Any]]:
        """Get conversation history for a specific topic.
        
        Args:
            guild_id: The Discord guild ID
            topic: The topic to search for
            
        Returns:
            List[Dict]: List of conversations containing the topic
        """
        topic_history = []
        
        for filename in os.listdir(self.conversations_dir):
            if filename.startswith(f"CONV_") and filename.endswith(f"_{guild_id}.json"):
                with open(os.path.join(self.conversations_dir, filename), "r") as f:
                    conv_data = json.load(f)
                    
                    if topic in conv_data["topics"]:
                        topic_history.append({
                            "conversation_id": conv_data["conversation_id"],
                            "timestamp": conv_data["timestamp"],
                            "message_count": conv_data["message_count"],
                            "summary": self._generate_topic_summary(conv_data, topic)
                        })
        
        # Sort by timestamp
        topic_history.sort(key=lambda x: x["timestamp"], reverse=True)
        return topic_history
    
    def _generate_topic_summary(self, conversation: Dict[str, Any], topic: str) -> str:
        """Generate a brief summary of a conversation focusing on a specific topic.
        
        Args:
            conversation: Conversation data
            topic: The topic to focus on
            
        Returns:
            str: Brief summary of the conversation
        """
        # Extract messages related to the topic
        topic_messages = []
        for msg in conversation["messages"]:
            if re.search(self.topic_patterns[topic], msg["content"].lower()):
                topic_messages.append(msg)
        
        if not topic_messages:
            return "No specific discussion found for this topic."
        
        # Generate summary
        summary = f"Discussion about {topic}:\n"
        for msg in topic_messages[:3]:  # Include up to 3 relevant messages
            summary += f"- {msg['content'][:100]}...\n"
        
        return summary 