import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
import re
import uuid
import logging
from utils.cache_manager import CacheManager

class UserAnalytics:
    def __init__(self, settings_dir: str):
        """Initialize the user analytics system.
        
        Args:
            settings_dir: Directory to store analytics data
        """
        self.settings_dir = settings_dir
        self.analytics_dir = os.path.join(settings_dir, "analytics")
        self.user_stats_dir = os.path.join(settings_dir, "user_stats")
        self.logger = logging.getLogger(__name__)
        
        # Create necessary directories
        os.makedirs(self.analytics_dir, exist_ok=True)
        os.makedirs(self.user_stats_dir, exist_ok=True)
        
        # Initialize analytics patterns
        self.code_patterns = {
            "python": r"```python\n(.*?)\n```",
            "javascript": r"```javascript\n(.*?)\n```",
            "java": r"```java\n(.*?)\n```",
            "cpp": r"```cpp\n(.*?)\n```",
            "sql": r"```sql\n(.*?)\n```",
            "html": r"```html\n(.*?)\n```",
            "css": r"```css\n(.*?)\n```",
            "markdown": r"```markdown\n(.*?)\n```"
        }
        
        self.topic_patterns = {
            "programming": r"(code|programming|function|class|method|api|bug|debug|error)",
            "math": r"(calculation|equation|formula|math|number|statistics)",
            "language": r"(grammar|sentence|word|language|translation|dictionary)",
            "general": r"(what|how|why|when|where|who|explain|describe|tell)"
        }
        
        # Initialize cache manager
        self.cache_manager = CacheManager(settings_dir)
        
        # Cache TTLs
        self.USER_STATS_TTL = 1800  # 30 minutes for user statistics
        self.GUILD_STATS_TTL = 3600  # 1 hour for guild statistics
    
    def _load_json(self, file_path: str) -> Optional[Dict]:
        """Load JSON data from a file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Dict if file exists and is valid JSON, None otherwise
        """
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            self.logger.error(f"Error loading JSON from {file_path}: {e}")
            return None
    
    def track_interaction(self, user_id: str, interaction_data: Dict) -> str:
        """Track a user interaction with metadata."""
        try:
            # Generate interaction ID
            interaction_id = str(uuid.uuid4())
            
            # Add timestamp and user ID
            interaction_data["timestamp"] = datetime.now().isoformat()
            interaction_data["user_id"] = user_id
            
            # Save interaction data
            interaction_file = os.path.join(self.analytics_dir, f"{interaction_id}.json")
            with open(interaction_file, "w", encoding="utf-8") as f:
                json.dump(interaction_data, f, indent=2)
            
            # Update user statistics
            self._update_user_stats(user_id, interaction_data)
            
            return interaction_id
            
        except Exception as e:
            print(f"Error tracking interaction: {e}")
            return None
    
    def _update_user_stats(self, user_id: str, interaction_data: Dict):
        """Update user statistics with new interaction data."""
        try:
            # Get current stats
            stats_file = os.path.join(self.user_stats_dir, f"{user_id}.json")
            stats = self._load_json(stats_file) or {
                "total_interactions": 0,
                "command_usage": {},
                "topic_engagement": {},
                "language_usage": {},
                "response_lengths": [],
                "last_updated": None
            }
            
            # Update basic stats
            stats["total_interactions"] += 1
            stats["last_updated"] = datetime.now().isoformat()
            
            # Update command usage
            command = interaction_data.get("command")
            if command:
                stats["command_usage"][command] = stats["command_usage"].get(command, 0) + 1
            
            # Update topic engagement
            if "topics" in interaction_data:
                for topic in interaction_data["topics"]:
                    stats["topic_engagement"][topic] = stats["topic_engagement"].get(topic, 0) + 1
            
            # Update language usage
            if "language" in interaction_data:
                lang = interaction_data["language"]
                stats["language_usage"][lang] = stats["language_usage"].get(lang, 0) + 1
            
            # Update response lengths
            if "response_length" in interaction_data:
                stats["response_lengths"].append(interaction_data["response_length"])
            
            # Save updated stats
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
                
        except Exception as e:
            print(f"Error updating user stats: {e}")
    
    def _get_top_items(self, counter: Dict[str, int], limit: int = 5) -> List[str]:
        """Get top items from a counter dictionary.
        
        Args:
            counter: Dictionary with item counts
            limit: Maximum number of items to return
            
        Returns:
            List of top items
        """
        return [item for item, _ in sorted(
            counter.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]]
    
    def get_user_stats(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific user.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            Optional[Dict]: User statistics if found, None otherwise
        """
        try:
            # Try to get from cache first
            cached_stats = self.cache_manager.get("user_stats", user_id)
            if cached_stats is not None:
                return cached_stats
            
            # If not in cache, load from disk
            stats_file = os.path.join(self.user_stats_dir, f"{user_id}.json")
            if not os.path.exists(stats_file):
                return None
            
            with open(stats_file, "r") as f:
                stats = json.load(f)
                
                # Cache the statistics
                self.cache_manager.set(
                    "user_stats",
                    user_id,
                    stats,
                    ttl=self.USER_STATS_TTL,
                    cache_type='memory'
                )
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Error getting user stats for {user_id}: {e}")
            return None
    
    def update_user_stats(self, user_id: str, stats_update: Dict[str, Any]) -> bool:
        """Update statistics for a user.
        
        Args:
            user_id: The Discord user ID
            stats_update: Dictionary containing stat updates
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get current stats
            current_stats = self.get_user_stats(user_id) or {}
            
            # Update stats
            for key, value in stats_update.items():
                if isinstance(value, (int, float)):
                    current_stats[key] = current_stats.get(key, 0) + value
                elif isinstance(value, dict):
                    if key not in current_stats:
                        current_stats[key] = {}
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, (int, float)):
                            current_stats[key][subkey] = current_stats[key].get(subkey, 0) + subvalue
                        else:
                            current_stats[key][subkey] = subvalue
                else:
                    current_stats[key] = value
            
            # Update timestamp
            current_stats["last_updated"] = datetime.now().isoformat()
            
            # Save to disk
            stats_file = os.path.join(self.user_stats_dir, f"{user_id}.json")
            with open(stats_file, "w") as f:
                json.dump(current_stats, f, indent=2)
            
            # Update cache
            self.cache_manager.set(
                "user_stats",
                user_id,
                current_stats,
                ttl=self.USER_STATS_TTL,
                cache_type='memory'
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating user stats for {user_id}: {e}")
            return False
    
    def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Generate insights about a user's interaction patterns.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            Dict containing user insights
        """
        stats = self.get_user_stats(user_id)
        if not stats:
            return {}
        
        # Calculate additional metrics
        active_days = len(stats["active_days"])
        first_interaction = datetime.fromisoformat(stats["first_interaction"])
        last_interaction = datetime.fromisoformat(stats["last_interaction"])
        days_since_first = (last_interaction - first_interaction).days + 1
        
        # Calculate engagement metrics
        interactions_per_day = stats["total_interactions"] / days_since_first
        active_days_ratio = active_days / days_since_first
        
        # Generate insights
        insights = {
            "engagement_level": self._calculate_engagement_level(
                interactions_per_day,
                active_days_ratio
            ),
            "interaction_patterns": {
                "total_interactions": stats["total_interactions"],
                "active_days": active_days,
                "interactions_per_day": round(interactions_per_day, 2),
                "active_days_ratio": round(active_days_ratio, 2)
            },
            "preferences": {
                "favorite_commands": stats["preferred_commands"],
                "favorite_topics": stats["preferred_topics"],
                "favorite_languages": stats["preferred_languages"]
            },
            "response_patterns": {
                "average_length": round(stats["average_response_length"], 2),
                "total_length": stats["total_response_length"]
            },
            "activity_timeline": {
                "first_interaction": stats["first_interaction"],
                "last_interaction": stats["last_interaction"],
                "days_active": days_since_first
            }
        }
        
        return insights
    
    def _calculate_engagement_level(self, interactions_per_day: float, active_days_ratio: float) -> str:
        """Calculate user engagement level.
        
        Args:
            interactions_per_day: Average number of interactions per day
            active_days_ratio: Ratio of active days to total days
            
        Returns:
            str: Engagement level description
        """
        if interactions_per_day >= 10 and active_days_ratio >= 0.8:
            return "Very High"
        elif interactions_per_day >= 5 and active_days_ratio >= 0.6:
            return "High"
        elif interactions_per_day >= 2 and active_days_ratio >= 0.4:
            return "Medium"
        elif interactions_per_day >= 1 and active_days_ratio >= 0.2:
            return "Low"
        else:
            return "Very Low"
    
    def get_guild_stats(self, guild_id: str) -> Dict[str, Any]:
        """Get statistics for all users in a guild.
        
        Args:
            guild_id: The Discord guild ID
            
        Returns:
            Dict containing guild statistics
        """
        try:
            # Try to get from cache first
            cache_key = f"guild_{guild_id}"
            cached_stats = self.cache_manager.get("guild_stats", cache_key)
            if cached_stats is not None:
                return cached_stats
            
            # If not in cache, compute statistics
            guild_stats = {
                "total_users": 0,
                "active_users": 0,
                "total_interactions": 0,
                "interactions_by_command": defaultdict(int),
                "interactions_by_topic": defaultdict(int),
                "interactions_by_language": defaultdict(int),
                "average_engagement": 0,
                "top_users": [],
                "command_usage": {},
                "topic_distribution": {},
                "language_distribution": {}
            }
            
            # Process all user stats
            user_stats_list = []
            for filename in os.listdir(self.user_stats_dir):
                if filename.endswith(".json"):
                    with open(os.path.join(self.user_stats_dir, filename), "r") as f:
                        user_stats = json.load(f)
                        if user_stats.get("guild_id") == guild_id:
                            user_stats_list.append(user_stats)
                            
                            # Update basic stats
                            guild_stats["total_users"] += 1
                            guild_stats["total_interactions"] += user_stats["total_interactions"]
                            
                            # Update command stats
                            for cmd, count in user_stats["interactions_by_command"].items():
                                guild_stats["interactions_by_command"][cmd] += count
                            
                            # Update topic stats
                            for topic, count in user_stats["interactions_by_topic"].items():
                                guild_stats["interactions_by_topic"][topic] += count
                            
                            # Update language stats
                            for lang, count in user_stats["interactions_by_language"].items():
                                guild_stats["interactions_by_language"][lang] += count
                            
                            # Consider user active if they have recent interactions
                            last_interaction = datetime.fromisoformat(user_stats["last_interaction"])
                            if (datetime.now() - last_interaction).days <= 7:
                                guild_stats["active_users"] += 1
            
            # Calculate averages and distributions
            if guild_stats["total_users"] > 0:
                guild_stats["average_engagement"] = guild_stats["total_interactions"] / guild_stats["total_users"]
            
            # Get top users by interaction count
            user_stats_list.sort(key=lambda x: x["total_interactions"], reverse=True)
            guild_stats["top_users"] = [
                {
                    "user_id": stats["user_id"],
                    "total_interactions": stats["total_interactions"],
                    "last_interaction": stats["last_interaction"]
                }
                for stats in user_stats_list[:5]  # Top 5 users
            ]
            
            # Calculate distributions
            total_commands = sum(guild_stats["interactions_by_command"].values())
            total_topics = sum(guild_stats["interactions_by_topic"].values())
            total_languages = sum(guild_stats["interactions_by_language"].values())
            
            if total_commands > 0:
                guild_stats["command_usage"] = {
                    cmd: count / total_commands
                    for cmd, count in guild_stats["interactions_by_command"].items()
                }
            
            if total_topics > 0:
                guild_stats["topic_distribution"] = {
                    topic: count / total_topics
                    for topic, count in guild_stats["interactions_by_topic"].items()
                }
            
            if total_languages > 0:
                guild_stats["language_distribution"] = {
                    lang: count / total_languages
                    for lang, count in guild_stats["interactions_by_language"].items()
                }
            
            # Cache the statistics
            self.cache_manager.set(
                "guild_stats",
                cache_key,
                guild_stats,
                ttl=self.GUILD_STATS_TTL,
                cache_type='disk'
            )
            
            return guild_stats
            
        except Exception as e:
            self.logger.error(f"Error getting guild stats for {guild_id}: {e}")
            return {
                "error": f"Failed to get guild statistics: {str(e)}"
            }
    
    def get_user_activity_report(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate an activity report for a user.
        
        Args:
            user_id: The Discord user ID
            days: Number of days to analyze
            
        Returns:
            Dict containing activity report
        """
        stats = self.get_user_stats(user_id)
        if not stats:
            return {}
        
        # Get date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Initialize report
        report = {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "activity_summary": {
                "total_interactions": 0,
                "active_days": 0,
                "average_interactions_per_day": 0,
                "most_active_day": None,
                "most_active_hour": None
            },
            "command_usage": defaultdict(int),
            "topic_engagement": defaultdict(int),
            "language_usage": defaultdict(int),
            "daily_activity": defaultdict(int),
            "hourly_activity": defaultdict(int)
        }
        
        # Process interactions
        for filename in os.listdir(self.analytics_dir):
            if filename.startswith(f"INT_") and filename.endswith(f"_{user_id}.json"):
                with open(os.path.join(self.analytics_dir, filename), "r") as f:
                    interaction = json.load(f)
                    
                    # Check if interaction is within date range
                    interaction_date = datetime.fromisoformat(interaction["timestamp"])
                    if start_date <= interaction_date <= end_date:
                        # Update activity summary
                        report["activity_summary"]["total_interactions"] += 1
                        
                        # Update command usage
                        if "command" in interaction:
                            report["command_usage"][interaction["command"]] += 1
                        
                        # Update topic engagement
                        if "content" in interaction:
                            content = interaction["content"].lower()
                            for topic, pattern in self.topic_patterns.items():
                                if re.search(pattern, content):
                                    report["topic_engagement"][topic] += 1
                        
                        # Update language usage
                        if "language" in interaction:
                            report["language_usage"][interaction["language"]] += 1
                        
                        # Update daily activity
                        day = interaction_date.date().isoformat()
                        report["daily_activity"][day] += 1
                        
                        # Update hourly activity
                        hour = interaction_date.hour
                        report["hourly_activity"][hour] += 1
        
        # Calculate averages and find most active times
        total_days = (end_date - start_date).days + 1
        report["activity_summary"]["active_days"] = len(report["daily_activity"])
        report["activity_summary"]["average_interactions_per_day"] = round(
            report["activity_summary"]["total_interactions"] / total_days,
            2
        )
        
        # Find most active day
        if report["daily_activity"]:
            most_active_day = max(
                report["daily_activity"].items(),
                key=lambda x: x[1]
            )
            report["activity_summary"]["most_active_day"] = {
                "date": most_active_day[0],
                "interactions": most_active_day[1]
            }
        
        # Find most active hour
        if report["hourly_activity"]:
            most_active_hour = max(
                report["hourly_activity"].items(),
                key=lambda x: x[1]
            )
            report["activity_summary"]["most_active_hour"] = {
                "hour": most_active_hour[0],
                "interactions": most_active_hour[1]
            }
        
        return report 