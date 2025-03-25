import json
import os
import traceback
import sys
from datetime import datetime
from typing import Dict, Optional, Any, List

class ErrorLogger:
    def __init__(self, settings_dir: str):
        self.settings_dir = settings_dir
        self.error_dir = os.path.join(settings_dir, "error_logs")
        os.makedirs(self.error_dir, exist_ok=True)

    def log_error(self, 
                  error: Exception,
                  command: Optional[str] = None,
                  user_id: Optional[str] = None,
                  guild_id: Optional[str] = None,
                  context: Optional[Dict[str, Any]] = None) -> str:
        """Log an error with context for analysis.
        
        Args:
            error: The exception that was raised
            command: The command that caused the error (if applicable)
            user_id: The Discord user ID (if applicable)
            guild_id: The Discord guild ID (if applicable)
            context: Additional context about the error
            
        Returns:
            str: The error log ID
        """
        # Create error entry
        error_entry = {
            "error_id": f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id or 'system'}",
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "command": command,
            "user_id": user_id,
            "guild_id": guild_id,
            "python_version": sys.version,
            "context": context or {},
            "suggested_fixes": self._generate_suggested_fixes(error)
        }
        
        # Save to file
        error_file = os.path.join(self.error_dir, f"{error_entry['error_id']}.json")
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_entry, f, indent=4, ensure_ascii=False)
        
        return error_entry['error_id']

    def _generate_suggested_fixes(self, error: Exception) -> Dict[str, Any]:
        """Generate suggested fixes based on the error type and message."""
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        suggestions = {
            "immediate_fixes": [],
            "preventive_measures": [],
            "improvement_suggestions": []
        }
        
        # Common error patterns and their fixes
        if "api key" in error_message:
            suggestions["immediate_fixes"].append("Check if the API key is properly set in the .env file")
            suggestions["preventive_measures"].append("Add API key validation on startup")
        
        if "rate limit" in error_message:
            suggestions["immediate_fixes"].append("Wait a few minutes before trying again")
            suggestions["preventive_measures"].append("Implement rate limiting handling")
        
        if "permission" in error_message:
            suggestions["immediate_fixes"].append("Check if the bot has the required permissions")
            suggestions["preventive_measures"].append("Add permission checks before executing commands")
        
        if "timeout" in error_message:
            suggestions["immediate_fixes"].append("Check your internet connection")
            suggestions["preventive_measures"].append("Implement request timeouts and retries")
        
        if "json" in error_message:
            suggestions["immediate_fixes"].append("Check if the response data is properly formatted")
            suggestions["preventive_measures"].append("Add JSON validation before processing")
        
        # Add general improvement suggestions
        suggestions["improvement_suggestions"].extend([
            "Add more detailed error logging",
            "Implement better error handling",
            "Add user-friendly error messages",
            "Consider adding fallback mechanisms"
        ])
        
        return suggestions

    def get_error(self, error_id: str) -> Optional[Dict]:
        """Retrieve error log by ID."""
        error_file = os.path.join(self.error_dir, f"{error_id}.json")
        if os.path.exists(error_file):
            with open(error_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def get_all_errors(self) -> List[Dict]:
        """Get all error logs."""
        error_entries = []
        for filename in os.listdir(self.error_dir):
            if filename.endswith('.json'):
                with open(os.path.join(self.error_dir, filename), 'r', encoding='utf-8') as f:
                    error_entries.append(json.load(f))
        return sorted(error_entries, key=lambda x: x['timestamp'], reverse=True)

    def get_errors_by_type(self, error_type: str) -> List[Dict]:
        """Get all errors of a specific type."""
        return [error for error in self.get_all_errors() 
                if error['error_type'] == error_type]

    def get_errors_by_user(self, user_id: str) -> List[Dict]:
        """Get all errors associated with a specific user."""
        return [error for error in self.get_all_errors() 
                if error['user_id'] == user_id] 