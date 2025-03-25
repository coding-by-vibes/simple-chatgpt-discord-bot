from typing import List, Dict, Optional
import openai
from datetime import datetime
import json
from pathlib import Path

class ConversationAnalyzer:
    def __init__(self, settings_dir: Path):
        self.settings_dir = settings_dir
        self.summaries_dir = settings_dir / "summaries"
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        
    def detect_topic_change(self, messages: List[Dict], threshold: float = 0.7) -> bool:
        """Detect if the conversation topic has changed significantly."""
        if len(messages) < 2:
            return False
            
        # Get the last two messages
        last_message = messages[-1]["content"]
        previous_message = messages[-2]["content"]
        
        # Use OpenAI to analyze topic similarity
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a topic analysis assistant. Compare two messages and determine if they are discussing significantly different topics. Respond with 'true' or 'false' only."},
                {"role": "user", "content": f"Message 1: {previous_message}\nMessage 2: {last_message}\nAre these messages discussing significantly different topics?"}
            ],
            max_tokens=10,
            temperature=0.3
        )
        
        return response.choices[0].message['content'].lower().strip() == 'true'
    
    def generate_summary(self, messages: List[Dict], max_tokens: int = 500) -> str:
        """Generate a summary of the conversation."""
        if not messages:
            return ""
            
        # Prepare messages for summarization
        conversation_text = "\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in messages
        ])
        
        # Use OpenAI to generate summary
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a conversation summarizer. Create a concise summary of the key points discussed."},
                {"role": "user", "content": f"Please summarize this conversation:\n\n{conversation_text}"}
            ],
            max_tokens=max_tokens,
            temperature=0.3
        )
        
        return response.choices[0].message['content']
    
    def manage_context_window(self, messages: List[Dict], max_tokens: int = 4000) -> List[Dict]:
        """Manage the context window by summarizing older messages if needed."""
        # Estimate tokens in current messages
        total_tokens = sum(len(msg["content"].split()) * 1.3 for msg in messages)
        
        if total_tokens <= max_tokens:
            return messages
            
        # Generate summary of older messages
        older_messages = messages[:-5]  # Keep last 5 messages
        summary = self.generate_summary(older_messages)
        
        # Create new context with summary and recent messages
        new_context = [
            {"role": "system", "content": f"Previous conversation summary: {summary}"},
            *messages[-5:]  # Keep last 5 messages
        ]
        
        return new_context
    
    def save_summary(self, guild_id: str, summary: str):
        """Save conversation summary to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.summaries_dir / f"{guild_id}_{timestamp}.json"
        
        summary_data = {
            "timestamp": timestamp,
            "summary": summary
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary_data, f, indent=4)
    
    def get_recent_summaries(self, guild_id: str, limit: int = 5) -> List[Dict]:
        """Get recent conversation summaries for a guild."""
        summaries = []
        for file in sorted(self.summaries_dir.glob(f"{guild_id}_*.json"), reverse=True)[:limit]:
            with open(file, 'r') as f:
                summaries.append(json.load(f))
        return summaries 