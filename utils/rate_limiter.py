from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
import threading
import logging
import json
import os
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class RateLimit:
    """Represents a rate limit configuration."""
    requests: int  # Number of requests allowed
    window: int   # Time window in seconds
    cooldown: int = 0  # Cooldown period in seconds after hitting limit

@dataclass
class RateLimitState:
    """Represents the current state of a rate limit."""
    requests: int  # Current number of requests
    window_start: datetime  # Start time of current window
    cooldown_end: Optional[datetime] = None  # End time of cooldown period

class RateLimiter:
    def __init__(self, settings_dir: str):
        """Initialize the rate limiter.
        
        Args:
            settings_dir: Directory to store rate limit data
        """
        self.settings_dir = settings_dir
        self.rate_limit_dir = os.path.join(settings_dir, "rate_limits")
        self.logger = logging.getLogger(__name__)
        
        # Create rate limit directory
        os.makedirs(self.rate_limit_dir, exist_ok=True)
        
        # Thread lock for thread safety
        self.lock = threading.Lock()
        
        # Initialize rate limits for different commands/operations
        self.rate_limits = {
            # General command limits - Starting with no cooldown
            "default": RateLimit(requests=30, window=10, cooldown=0),  # 30 requests per 10 seconds, no cooldown
            "high_cost": RateLimit(requests=10, window=30, cooldown=0),  # 10 requests per 30 seconds, no cooldown
            
            # Specific command limits - Also starting with no cooldown
            "askgpt": RateLimit(requests=10, window=60, cooldown=0),  # 10 requests per minute
            "analyze_code": RateLimit(requests=5, window=300, cooldown=0),  # 5 requests per 5 minutes
            "summarize": RateLimit(requests=5, window=120, cooldown=0),  # 5 requests per 2 minutes
            "wiki": RateLimit(requests=10, window=60, cooldown=0),  # 10 requests per minute
            
            # Analytics and stats commands
            "analytics": RateLimit(requests=5, window=60, cooldown=0),  # 5 requests per minute
            "user_analytics": RateLimit(requests=5, window=60, cooldown=0),  # 5 requests per minute
            "guild_analytics": RateLimit(requests=5, window=60, cooldown=0),  # 5 requests per minute
            
            # User-specific global limit
            "user_global": RateLimit(requests=60, window=60, cooldown=0),  # 60 requests per minute per user
            
            # Guild-specific global limit
            "guild_global": RateLimit(requests=200, window=60, cooldown=0)  # 200 requests per minute per guild
        }
        
        # Load custom rate limits if they exist
        self._load_custom_limits()
        
        # Initialize rate limit states
        self.states: Dict[str, Dict[str, RateLimitState]] = defaultdict(dict)
        
        # Load existing states
        self._load_states()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "rate_limited_requests": 0,
            "rate_limits_by_command": defaultdict(int),
            "rate_limits_by_user": defaultdict(int),
            "rate_limits_by_guild": defaultdict(int)
        }
    
    def update_rate_limit(self, command: str, requests: int, window: int, cooldown: int = 0) -> bool:
        """Update rate limit settings for a command.
        
        Args:
            command: The command to update
            requests: Number of requests allowed
            window: Time window in seconds
            cooldown: Cooldown period in seconds after hitting limit
            
        Returns:
            bool: True if update successful
        """
        try:
            with self.lock:
                self.rate_limits[command] = RateLimit(
                    requests=requests,
                    window=window,
                    cooldown=cooldown
                )
                self._save_custom_limits()
            return True
        except Exception as e:
            self.logger.error(f"Error updating rate limit for {command}: {e}")
            return False
    
    def _save_custom_limits(self):
        """Save custom rate limits to disk."""
        try:
            limits_file = os.path.join(self.rate_limit_dir, "custom_limits.json")
            with open(limits_file, "w") as f:
                # Convert rate limits to serializable format
                serialized_limits = {
                    cmd: {
                        "requests": limit.requests,
                        "window": limit.window,
                        "cooldown": limit.cooldown
                    }
                    for cmd, limit in self.rate_limits.items()
                }
                json.dump(serialized_limits, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving custom rate limits: {e}")
    
    def _load_custom_limits(self):
        """Load custom rate limits from disk."""
        try:
            limits_file = os.path.join(self.rate_limit_dir, "custom_limits.json")
            if os.path.exists(limits_file):
                with open(limits_file, "r") as f:
                    serialized_limits = json.load(f)
                    for cmd, limit_data in serialized_limits.items():
                        self.rate_limits[cmd] = RateLimit(
                            requests=limit_data["requests"],
                            window=limit_data["window"],
                            cooldown=limit_data["cooldown"]
                        )
        except Exception as e:
            self.logger.error(f"Error loading custom rate limits: {e}")
    
    def check_rate_limit(self, command: str, user_id: str, guild_id: str = None) -> Tuple[bool, Optional[float]]:
        """Check if a request should be rate limited.
        
        Args:
            command: The command being executed
            user_id: The user's ID
            guild_id: Optional guild ID
            
        Returns:
            Tuple[bool, Optional[float]]: (is_allowed, seconds_until_reset)
        """
        with self.lock:
            now = datetime.utcnow()
            self.stats["total_requests"] += 1
            
            # Check command-specific limit
            command_key = f"cmd:{command}:{user_id}"
            if not self._check_limit(command_key, command, now):
                self._update_stats("rate_limited", command, user_id, guild_id)
                return False, self._get_reset_time(command_key, command)
            
            # Check user global limit
            user_key = f"user:{user_id}"
            if not self._check_limit(user_key, "user_global", now):
                self._update_stats("rate_limited", command, user_id, guild_id)
                return False, self._get_reset_time(user_key, "user_global")
            
            # Check guild limit if applicable
            if guild_id:
                guild_key = f"guild:{guild_id}"
                if not self._check_limit(guild_key, "guild_global", now):
                    self._update_stats("rate_limited", command, user_id, guild_id)
                    return False, self._get_reset_time(guild_key, "guild_global")
            
            return True, None
    
    def _check_limit(self, key: str, limit_type: str, now: datetime) -> bool:
        """Check if a specific rate limit has been exceeded.
        
        Args:
            key: The rate limit key
            limit_type: Type of rate limit to check
            now: Current timestamp
            
        Returns:
            bool: True if request is allowed, False if rate limited
        """
        # Get rate limit configuration
        limit = self.rate_limits.get(limit_type, self.rate_limits["default"])
        
        # Get or create state
        if key not in self.states:
            self.states[key] = RateLimitState(
                requests=0,
                window_start=now
            )
        state = self.states[key]
        
        # Check if in cooldown
        if state.cooldown_end and now < state.cooldown_end:
            return False
        
        # Check if window has expired
        window_end = state.window_start + timedelta(seconds=limit.window)
        if now >= window_end:
            # Reset window
            state.requests = 0
            state.window_start = now
            state.cooldown_end = None
        
        # Check if limit exceeded
        if state.requests >= limit.requests:
            # Start cooldown if configured
            if limit.cooldown > 0:
                state.cooldown_end = now + timedelta(seconds=limit.cooldown)
            return False
        
        # Increment request count
        state.requests += 1
        return True
    
    def _get_reset_time(self, key: str, limit_type: str) -> float:
        """Get seconds until rate limit resets.
        
        Args:
            key: The rate limit key
            limit_type: Type of rate limit
            
        Returns:
            float: Seconds until reset
        """
        now = datetime.utcnow()
        state = self.states.get(key)
        limit = self.rate_limits.get(limit_type, self.rate_limits["default"])
        
        if not state:
            return 0
        
        # Check cooldown first
        if state.cooldown_end and now < state.cooldown_end:
            return (state.cooldown_end - now).total_seconds()
        
        # Calculate window reset time
        window_end = state.window_start + timedelta(seconds=limit.window)
        if now < window_end:
            return (window_end - now).total_seconds()
        
        return 0
    
    def _update_stats(self, stat_type: str, command: str, user_id: str, guild_id: str = None):
        """Update rate limiting statistics.
        
        Args:
            stat_type: Type of statistic to update
            command: Command that was rate limited
            user_id: User ID
            guild_id: Optional guild ID
        """
        if stat_type == "rate_limited":
            self.stats["rate_limited_requests"] += 1
            self.stats["rate_limits_by_command"][command] += 1
            self.stats["rate_limits_by_user"][user_id] += 1
            if guild_id:
                self.stats["rate_limits_by_guild"][guild_id] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics.
        
        Returns:
            Dict containing rate limit statistics
        """
        with self.lock:
            return {
                "total_requests": self.stats["total_requests"],
                "rate_limited_requests": self.stats["rate_limited_requests"],
                "rate_limit_percentage": (
                    self.stats["rate_limited_requests"] / self.stats["total_requests"] * 100
                    if self.stats["total_requests"] > 0 else 0
                ),
                "most_limited_commands": dict(sorted(
                    self.stats["rate_limits_by_command"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]),
                "most_limited_users": dict(sorted(
                    self.stats["rate_limits_by_user"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]),
                "most_limited_guilds": dict(sorted(
                    self.stats["rate_limits_by_guild"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5])
            }
    
    def _save_states(self):
        """Save rate limit states to disk."""
        try:
            state_file = os.path.join(self.rate_limit_dir, "states.json")
            with open(state_file, "w") as f:
                # Convert states to serializable format
                serialized_states = {}
                for key, state in self.states.items():
                    serialized_states[key] = {
                        "requests": state.requests,
                        "window_start": state.window_start.isoformat(),
                        "cooldown_end": state.cooldown_end.isoformat() if state.cooldown_end else None
                    }
                json.dump(serialized_states, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving rate limit states: {e}")
    
    def _load_states(self):
        """Load rate limit states from disk."""
        try:
            state_file = os.path.join(self.rate_limit_dir, "states.json")
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    serialized_states = json.load(f)
                    for key, state_data in serialized_states.items():
                        self.states[key] = RateLimitState(
                            requests=state_data["requests"],
                            window_start=datetime.fromisoformat(state_data["window_start"]),
                            cooldown_end=(
                                datetime.fromisoformat(state_data["cooldown_end"])
                                if state_data["cooldown_end"] else None
                            )
                        )
        except Exception as e:
            self.logger.error(f"Error loading rate limit states: {e}")
    
    def reset_limits(self, user_id: str = None, guild_id: str = None):
        """Reset rate limits for a user or guild.
        
        Args:
            user_id: Optional user ID to reset
            guild_id: Optional guild ID to reset
        """
        with self.lock:
            now = datetime.utcnow()
            
            if user_id:
                # Reset user-specific limits
                prefix = f"cmd:"
                user_keys = [k for k in self.states.keys() if k.endswith(f":{user_id}")]
                for key in user_keys:
                    self.states[key] = RateLimitState(requests=0, window_start=now)
                
                # Reset user global limit
                user_key = f"user:{user_id}"
                if user_key in self.states:
                    self.states[user_key] = RateLimitState(requests=0, window_start=now)
            
            if guild_id:
                # Reset guild limit
                guild_key = f"guild:{guild_id}"
                if guild_key in self.states:
                    self.states[guild_key] = RateLimitState(requests=0, window_start=now)
            
            # If no specific reset, clear all
            if not user_id and not guild_id:
                self.states.clear()
            
            # Save updated states
            self._save_states() 