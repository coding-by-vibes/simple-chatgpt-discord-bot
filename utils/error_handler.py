import traceback
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os
from enum import Enum

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    API = "api"
    NETWORK = "network"
    DATABASE = "database"
    PERMISSION = "permission"
    VALIDATION = "validation"
    RATE_LIMIT = "rate_limit"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class ErrorHandler:
    def __init__(self, settings_dir: str):
        """Initialize the error handler.
        
        Args:
            settings_dir: Directory to store error logs and recovery data
        """
        self.settings_dir = settings_dir
        self.error_logs_dir = os.path.join(settings_dir, "error_logs")
        self.recovery_data_dir = os.path.join(settings_dir, "recovery_data")
        
        # Create necessary directories
        os.makedirs(self.error_logs_dir, exist_ok=True)
        os.makedirs(self.recovery_data_dir, exist_ok=True)
        
        # Load recovery strategies
        self.recovery_strategies = self._load_recovery_strategies()
        
    def _load_recovery_strategies(self) -> Dict[str, Dict]:
        """Load predefined recovery strategies for different error types."""
        return {
            ErrorCategory.API.value: {
                "retry_count": 3,
                "backoff_factor": 2,
                "max_wait": 30,
                "actions": [
                    "Verify API key validity",
                    "Check API endpoint status",
                    "Validate request parameters"
                ]
            },
            ErrorCategory.NETWORK.value: {
                "retry_count": 3,
                "backoff_factor": 1.5,
                "max_wait": 20,
                "actions": [
                    "Check internet connection",
                    "Verify server availability",
                    "Test network connectivity"
                ]
            },
            ErrorCategory.DATABASE.value: {
                "retry_count": 2,
                "backoff_factor": 1,
                "max_wait": 10,
                "actions": [
                    "Verify database connection",
                    "Check database permissions",
                    "Validate data integrity"
                ]
            },
            ErrorCategory.PERMISSION.value: {
                "retry_count": 1,
                "backoff_factor": 1,
                "max_wait": 5,
                "actions": [
                    "Verify user permissions",
                    "Check role assignments",
                    "Validate access tokens"
                ]
            },
            ErrorCategory.VALIDATION.value: {
                "retry_count": 1,
                "backoff_factor": 1,
                "max_wait": 5,
                "actions": [
                    "Validate input parameters",
                    "Check data format",
                    "Verify required fields"
                ]
            },
            ErrorCategory.RATE_LIMIT.value: {
                "retry_count": 5,
                "backoff_factor": 2,
                "max_wait": 60,
                "actions": [
                    "Implement exponential backoff",
                    "Check rate limit headers",
                    "Adjust request timing"
                ]
            },
            ErrorCategory.CRITICAL.value: {
                "retry_count": 1,
                "backoff_factor": 1,
                "max_wait": 5,
                "actions": [
                    "Check system logs",
                    "Verify system state",
                    "Contact system administrator"
                ]
            },
            ErrorCategory.UNKNOWN.value: {
                "retry_count": 1,
                "backoff_factor": 1,
                "max_wait": 5,
                "actions": [
                    "Check system logs",
                    "Verify system state",
                    "Contact system administrator"
                ]
            }
        }
    
    def analyze_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze an error and determine its severity and category.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            Dict containing error analysis
        """
        error_type = type(error).__name__
        error_message = str(error)
        traceback_info = traceback.format_exc()
        
        # Determine error category
        category = self._determine_error_category(error, error_message)
        
        # Determine error severity
        severity = self._determine_error_severity(error, category, context)
        
        # Get recovery strategy
        strategy = self.recovery_strategies.get(category.value, self.recovery_strategies[ErrorCategory.UNKNOWN.value])
        
        return {
            "error_type": error_type,
            "error_message": error_message,
            "category": category.value,
            "severity": severity.value,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback_info,
            "context": context or {},
            "recovery_strategy": strategy
        }
    
    def _determine_error_category(self, error: Exception, error_message: str) -> ErrorCategory:
        """Determine the category of an error based on its type and message."""
        error_message = error_message.lower()
        
        if "api" in error_message or "openai" in error_message:
            return ErrorCategory.API
        elif "network" in error_message or "connection" in error_message:
            return ErrorCategory.NETWORK
        elif "database" in error_message or "sql" in error_message:
            return ErrorCategory.DATABASE
        elif "permission" in error_message or "access" in error_message:
            return ErrorCategory.PERMISSION
        elif "validation" in error_message or "invalid" in error_message:
            return ErrorCategory.VALIDATION
        elif "rate limit" in error_message or "too many requests" in error_message:
            return ErrorCategory.RATE_LIMIT
        else:
            return ErrorCategory.UNKNOWN
    
    def _determine_error_severity(self, error: Exception, category: ErrorCategory, context: Dict[str, Any] = None) -> ErrorSeverity:
        """Determine the severity of an error based on its category and context."""
        if category == ErrorCategory.CRITICAL:
            return ErrorSeverity.CRITICAL
        
        # Check for critical operations in context
        if context and context.get("critical_operation", False):
            return ErrorSeverity.HIGH
        
        # Rate limit errors are usually high severity
        if category == ErrorCategory.RATE_LIMIT:
            return ErrorSeverity.HIGH
        
        # API errors are usually medium severity
        if category == ErrorCategory.API:
            return ErrorSeverity.MEDIUM
        
        # Network errors are usually medium severity
        if category == ErrorCategory.NETWORK:
            return ErrorSeverity.MEDIUM
        
        # Database errors are usually high severity
        if category == ErrorCategory.DATABASE:
            return ErrorSeverity.HIGH
        
        # Permission errors are usually medium severity
        if category == ErrorCategory.PERMISSION:
            return ErrorSeverity.MEDIUM
        
        # Validation errors are usually low severity
        if category == ErrorCategory.VALIDATION:
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None) -> str:
        """Log an error with analysis and recovery information.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            
        Returns:
            str: Error ID for reference
        """
        # Analyze the error
        analysis = self.analyze_error(error, context)
        
        # Generate error ID
        error_id = f"ERR_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{analysis['error_type'][:8]}"
        
        # Add error ID to analysis
        analysis["error_id"] = error_id
        
        # Save error log
        log_file = os.path.join(self.error_logs_dir, f"{error_id}.json")
        with open(log_file, "w") as f:
            json.dump(analysis, f, indent=2)
        
        return error_id
    
    def get_error(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve error information by ID.
        
        Args:
            error_id: The ID of the error to retrieve
            
        Returns:
            Optional[Dict]: Error information if found, None otherwise
        """
        log_file = os.path.join(self.error_logs_dir, f"{error_id}.json")
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                return json.load(f)
        return None
    
    def get_recovery_actions(self, error_id: str) -> List[str]:
        """Get recommended recovery actions for an error.
        
        Args:
            error_id: The ID of the error
            
        Returns:
            List[str]: List of recommended recovery actions
        """
        error_info = self.get_error(error_id)
        if not error_info:
            return []
        
        strategy = error_info.get("recovery_strategy", {})
        return strategy.get("actions", [])
    
    def save_recovery_data(self, error_id: str, recovery_data: Dict[str, Any]) -> bool:
        """Save recovery attempt data for an error.
        
        Args:
            error_id: The ID of the error
            recovery_data: Data about the recovery attempt
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            recovery_file = os.path.join(self.recovery_data_dir, f"{error_id}_recovery.json")
            with open(recovery_file, "w") as f:
                json.dump(recovery_data, f, indent=2)
            return True
        except Exception:
            return False
    
    def get_recovery_data(self, error_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve recovery attempt data for an error.
        
        Args:
            error_id: The ID of the error
            
        Returns:
            Optional[Dict]: Recovery data if found, None otherwise
        """
        recovery_file = os.path.join(self.recovery_data_dir, f"{error_id}_recovery.json")
        if os.path.exists(recovery_file):
            with open(recovery_file, "r") as f:
                return json.load(f)
        return None
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get statistics about logged errors.
        
        Returns:
            Dict containing error statistics
        """
        stats = {
            "total_errors": 0,
            "errors_by_category": {},
            "errors_by_severity": {},
            "recent_errors": []
        }
        
        # Count errors in each category and severity
        for filename in os.listdir(self.error_logs_dir):
            if filename.endswith(".json"):
                with open(os.path.join(self.error_logs_dir, filename), "r") as f:
                    error_info = json.load(f)
                    
                    stats["total_errors"] += 1
                    
                    # Count by category
                    category = error_info["category"]
                    stats["errors_by_category"][category] = stats["errors_by_category"].get(category, 0) + 1
                    
                    # Count by severity
                    severity = error_info["severity"]
                    stats["errors_by_severity"][severity] = stats["errors_by_severity"].get(severity, 0) + 1
                    
                    # Add to recent errors
                    stats["recent_errors"].append({
                        "id": error_info["error_id"],
                        "type": error_info["error_type"],
                        "category": category,
                        "severity": severity,
                        "timestamp": error_info["timestamp"]
                    })
        
        # Sort recent errors by timestamp
        stats["recent_errors"].sort(key=lambda x: x["timestamp"], reverse=True)
        stats["recent_errors"] = stats["recent_errors"][:10]  # Keep only last 10 