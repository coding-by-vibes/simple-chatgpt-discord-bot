import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import re
from collections import Counter

class ConversationAnalyzer:
    def __init__(self, settings_dir: Path):
        """Initialize the conversation analyzer.
        
        Args:
            settings_dir: Path to settings directory
        """
        self.settings_dir = settings_dir
        self.summaries_dir = settings_dir / "summaries"
        self.logger = logging.getLogger(__name__)
        
        # Create necessary directories
        self.summaries_dir.mkdir(exist_ok=True)
        
    def analyze_conversation(self, messages: List[Dict]) -> Dict[str, Any]:
        """Analyze a conversation and return statistics and insights.
        
        Args:
            messages: List of message dictionaries with 'content' and 'author' keys
            
        Returns:
            Dict containing analysis results
        """
        try:
            if not messages:
                return self._create_empty_analysis()
                
            # Basic statistics
            total_messages = len(messages)
            unique_participants = len(set(msg['author'] for msg in messages))
            avg_message_length = sum(len(msg['content']) for msg in messages) / total_messages
            
            # Time analysis
            timestamps = [datetime.fromisoformat(msg['timestamp']) for msg in messages if 'timestamp' in msg]
            if timestamps:
                duration = max(timestamps) - min(timestamps)
                duration_minutes = duration.total_seconds() / 60
            else:
                duration_minutes = 0
                
            # Message distribution
            author_counts = Counter(msg['author'] for msg in messages)
            most_active = author_counts.most_common(1)[0] if author_counts else ('None', 0)
            
            # Topic analysis
            topics = self._detect_topics(messages)
            current_topic = topics[-1] if topics else 'Unknown'
            
            # Sentiment analysis
            sentiment = self._analyze_sentiment(messages)
            
            return {
                "total_messages": total_messages,
                "unique_participants": unique_participants,
                "average_message_length": avg_message_length,
                "duration_minutes": duration_minutes,
                "most_active_participant": {
                    "name": most_active[0],
                    "messages": most_active[1]
                },
                "topics": topics,
                "current_topic": current_topic,
                "sentiment": sentiment,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing conversation: {e}")
            return self._create_empty_analysis()
            
    def _create_empty_analysis(self) -> Dict[str, Any]:
        """Create an empty analysis result."""
        return {
            "total_messages": 0,
            "unique_participants": 0,
            "average_message_length": 0,
            "duration_minutes": 0,
            "most_active_participant": {
                "name": "None",
                "messages": 0
            },
            "topics": [],
            "current_topic": "None",
            "sentiment": "neutral",
            "timestamp": datetime.now().isoformat()
        }
        
    def _detect_topics(self, messages: List[Dict]) -> List[str]:
        """Detect topics in conversation messages."""
        try:
            # Simple topic detection based on keyword frequency
            topic_keywords = {
                "programming": ["code", "programming", "function", "bug", "error"],
                "help": ["help", "support", "assist", "guidance"],
                "general": ["chat", "talk", "discuss"],
                "settings": ["setting", "configure", "preference"],
                "persona": ["persona", "personality", "behavior"],
                "system": ["bot", "command", "feature"]
            }
            
            topics = []
            for msg in messages:
                content = msg['content'].lower()
                for topic, keywords in topic_keywords.items():
                    if any(keyword in content for keyword in keywords):
                        topics.append(topic)
                        
            return topics or ["general"]
            
        except Exception as e:
            self.logger.error(f"Error detecting topics: {e}")
            return ["general"]
            
    def _analyze_sentiment(self, messages: List[Dict]) -> str:
        """Simple sentiment analysis of messages."""
        try:
            positive_words = {"good", "great", "awesome", "thanks", "helpful", "nice", "love", "perfect"}
            negative_words = {"bad", "wrong", "error", "issue", "problem", "bug", "fail", "broken"}
            
            positive_count = 0
            negative_count = 0
            
            for msg in messages:
                content = msg['content'].lower()
                words = set(re.findall(r'\w+', content))
                positive_count += len(words & positive_words)
                negative_count += len(words & negative_words)
                
            if positive_count > negative_count:
                return "positive"
            elif negative_count > positive_count:
                return "negative"
            return "neutral"
            
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")
            return "neutral"
            
    def save_analysis(self, conversation_id: str, analysis: Dict) -> bool:
        """Save conversation analysis to file."""
        try:
            file_path = self.summaries_dir / f"{conversation_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Error saving analysis: {e}")
            return False
            
    def get_analysis(self, conversation_id: str) -> Optional[Dict]:
        """Get saved conversation analysis."""
        try:
            file_path = self.summaries_dir / f"{conversation_id}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Error getting analysis: {e}")
            return None 