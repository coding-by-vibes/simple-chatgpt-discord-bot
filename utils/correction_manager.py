import json
import os
from typing import List, Dict, Optional
from datetime import datetime

class CorrectionManager:
    def __init__(self, settings_dir: str):
        self.settings_dir = settings_dir
        self.corrections_dir = os.path.join(settings_dir, "corrections")
        os.makedirs(self.corrections_dir, exist_ok=True)

    def save_correction(self, 
                       user_id: str,
                       original_message: str,
                       correction: str,
                       context: Dict,
                       message_id: str) -> str:
        """Save a user correction.
        
        Args:
            user_id: The Discord user ID
            original_message: The original bot message
            correction: The user's correction
            context: Additional context (conversation history, etc.)
            message_id: The Discord message ID
            
        Returns:
            str: The correction ID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        correction_id = f"correction_{user_id}_{timestamp}"
        
        data = {
            "correction_id": correction_id,
            "user_id": user_id,
            "timestamp": timestamp,
            "original_message": original_message,
            "correction": correction,
            "context": context,
            "message_id": message_id,
            "status": "pending"  # pending, reviewed, accepted, rejected
        }
        
        filepath = os.path.join(self.corrections_dir, f"{correction_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        return correction_id

    def get_correction(self, correction_id: str) -> Optional[Dict]:
        """Get a specific correction by ID.
        
        Args:
            correction_id: The correction ID
            
        Returns:
            Optional[Dict]: The correction data if found, None otherwise
        """
        filepath = os.path.join(self.corrections_dir, f"{correction_id}.json")
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_user_corrections(self, user_id: str) -> List[Dict]:
        """Get all corrections submitted by a user.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            List[Dict]: List of corrections
        """
        corrections = []
        for filename in os.listdir(self.corrections_dir):
            if filename.startswith(f"correction_{user_id}_"):
                with open(os.path.join(self.corrections_dir, filename), 'r', 
                         encoding='utf-8') as f:
                    corrections.append(json.load(f))
        return sorted(corrections, key=lambda x: x['timestamp'], reverse=True)

    def get_all_corrections(self, status: Optional[str] = None) -> List[Dict]:
        """Get all corrections, optionally filtered by status.
        
        Args:
            status: Optional status filter (pending, reviewed, accepted, rejected)
            
        Returns:
            List[Dict]: List of corrections
        """
        corrections = []
        for filename in os.listdir(self.corrections_dir):
            with open(os.path.join(self.corrections_dir, filename), 'r', 
                     encoding='utf-8') as f:
                correction = json.load(f)
                if status is None or correction['status'] == status:
                    corrections.append(correction)
        return sorted(corrections, key=lambda x: x['timestamp'], reverse=True)

    def update_correction_status(self, correction_id: str, 
                               status: str, 
                               admin_id: str,
                               notes: Optional[str] = None) -> bool:
        """Update the status of a correction.
        
        Args:
            correction_id: The correction ID
            status: New status (pending, reviewed, accepted, rejected)
            admin_id: The Discord admin ID who made the update
            notes: Optional notes about the update
            
        Returns:
            bool: True if successful, False otherwise
        """
        correction = self.get_correction(correction_id)
        if not correction:
            return False
            
        correction['status'] = status
        correction['reviewed_by'] = admin_id
        correction['reviewed_at'] = datetime.now().isoformat()
        if notes:
            correction['review_notes'] = notes
            
        filepath = os.path.join(self.corrections_dir, f"{correction_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(correction, f, indent=4, ensure_ascii=False)
            
        return True 