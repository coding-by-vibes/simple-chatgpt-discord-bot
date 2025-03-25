import json
import os
from datetime import datetime
from typing import Dict, List, Optional

class FeedbackManager:
    def __init__(self, settings_dir: str):
        self.settings_dir = settings_dir
        self.feedback_dir = os.path.join(settings_dir, "feedback")
        os.makedirs(self.feedback_dir, exist_ok=True)

    def save_feedback(self, user_id: str, feedback: str, conversation_history: List[Dict], context_lines: int = 5) -> str:
        """Save user feedback with relevant conversation history.
        
        Args:
            user_id: The Discord user ID
            feedback: The user's feedback message
            conversation_history: List of conversation messages
            context_lines: Number of previous messages to include for context
            
        Returns:
            str: The feedback ID
        """
        # Create feedback entry
        feedback_entry = {
            "feedback_id": f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}",
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "feedback": feedback,
            "context": {
                "messages": conversation_history[-context_lines:] if conversation_history else [],
                "total_messages": len(conversation_history) if conversation_history else 0
            }
        }
        
        # Save to file
        feedback_file = os.path.join(self.feedback_dir, f"{feedback_entry['feedback_id']}.json")
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedback_entry, f, indent=4, ensure_ascii=False)
        
        return feedback_entry['feedback_id']

    def get_feedback(self, feedback_id: str) -> Optional[Dict]:
        """Retrieve feedback by ID."""
        feedback_file = os.path.join(self.feedback_dir, f"{feedback_id}.json")
        if os.path.exists(feedback_file):
            with open(feedback_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def get_all_feedback(self) -> List[Dict]:
        """Get all feedback entries."""
        feedback_entries = []
        for filename in os.listdir(self.feedback_dir):
            if filename.endswith('.json'):
                with open(os.path.join(self.feedback_dir, filename), 'r', encoding='utf-8') as f:
                    feedback_entries.append(json.load(f))
        return sorted(feedback_entries, key=lambda x: x['timestamp'], reverse=True) 