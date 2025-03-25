"""
Analytics and Reporting Module
This module provides functionality for tracking and analyzing bot usage, user behavior, and system performance.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass, asdict
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

@dataclass
class AnalyticsEvent:
    """Represents an analytics event with metadata."""
    event_type: str
    timestamp: datetime
    user_id: str
    guild_id: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

class AnalyticsManager:
    def __init__(self, data_dir: str):
        """Initialize the analytics manager.
        
        Args:
            data_dir: Directory to store analytics data
        """
        self.data_dir = data_dir
        self.events_file = os.path.join(data_dir, "analytics_events.json")
        self.logger = logging.getLogger(__name__)
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize events list
        self.events = self._load_events()
        
        # Initialize guild data directory
        self.guild_data_dir = os.path.join(data_dir, "guild_data")
        os.makedirs(self.guild_data_dir, exist_ok=True)
    
    def _load_events(self) -> List[AnalyticsEvent]:
        """Load analytics events from file."""
        if os.path.exists(self.events_file):
            try:
                with open(self.events_file, 'r') as f:
                    events_data = json.load(f)
                return [AnalyticsEvent(**event) for event in events_data]
            except Exception as e:
                self.logger.error(f"Error loading analytics events: {e}")
                return []
        return []
    
    def _save_events(self):
        """Save analytics events to file."""
        try:
            with open(self.events_file, 'w') as f:
                json.dump([asdict(event) for event in self.events], f, default=str)
        except Exception as e:
            self.logger.error(f"Error saving analytics events: {e}")
    
    def track_event(self, event_type: str, user_id: str, guild_id: str, 
                   data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
        """Track a new analytics event.
        
        Args:
            event_type: Type of event (e.g., 'command_used', 'error_occurred')
            user_id: ID of the user who triggered the event
            guild_id: ID of the guild where the event occurred
            data: Event-specific data
            metadata: Optional additional metadata
        """
        event = AnalyticsEvent(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            guild_id=guild_id,
            data=data,
            metadata=metadata
        )
        self.events.append(event)
        self._save_events()
    
    def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for the specified time period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary containing usage statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_date]
        
        # Convert events to DataFrame for analysis
        df = pd.DataFrame([asdict(e) for e in recent_events])
        
        stats = {
            "total_events": len(recent_events),
            "unique_users": df['user_id'].nunique(),
            "unique_guilds": df['guild_id'].nunique(),
            "events_by_type": df['event_type'].value_counts().to_dict(),
            "events_by_hour": df.groupby(df['timestamp'].dt.hour).size().to_dict(),
            "events_by_day": df.groupby(df['timestamp'].dt.date).size().to_dict()
        }
        
        return stats
    
    def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get analytics for a specific user.
        
        Args:
            user_id: ID of the user to analyze
            days: Number of days to analyze
            
        Returns:
            Dictionary containing user analytics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        user_events = [e for e in self.events if e.user_id == user_id and e.timestamp >= cutoff_date]
        
        if not user_events:
            return {"error": "No data found for user"}
        
        df = pd.DataFrame([asdict(e) for e in user_events])
        
        analytics = {
            "total_events": len(user_events),
            "unique_guilds": df['guild_id'].nunique(),
            "events_by_type": df['event_type'].value_counts().to_dict(),
            "events_by_hour": df.groupby(df['timestamp'].dt.hour).size().to_dict(),
            "events_by_day": df.groupby(df['timestamp'].dt.date).size().to_dict(),
            "most_used_commands": df[df['event_type'] == 'command_used']['data'].apply(
                lambda x: x.get('command', 'unknown')
            ).value_counts().head(5).to_dict()
        }
        
        return analytics
    
    def get_guild_analytics(self, guild_id: str, days: int = 30) -> Dict[str, Any]:
        """Get analytics for a specific guild.
        
        Args:
            guild_id: ID of the guild to analyze
            days: Number of days to analyze
            
        Returns:
            Dictionary containing guild analytics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        guild_events = [e for e in self.events if e.guild_id == guild_id and e.timestamp >= cutoff_date]
        
        if not guild_events:
            return {"error": "No data found for guild"}
        
        df = pd.DataFrame([asdict(e) for e in guild_events])
        
        analytics = {
            "total_events": len(guild_events),
            "unique_users": df['user_id'].nunique(),
            "events_by_type": df['event_type'].value_counts().to_dict(),
            "events_by_hour": df.groupby(df['timestamp'].dt.hour).size().to_dict(),
            "events_by_day": df.groupby(df['timestamp'].dt.date).size().to_dict(),
            "most_active_users": df.groupby('user_id').size().sort_values(ascending=False).head(5).to_dict(),
            "most_used_commands": df[df['event_type'] == 'command_used']['data'].apply(
                lambda x: x.get('command', 'unknown')
            ).value_counts().head(5).to_dict()
        }
        
        return analytics
    
    def generate_usage_graph(self, days: int = 30) -> BytesIO:
        """Generate a graph showing usage over time.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            BytesIO object containing the graph image
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_date]
        
        if not recent_events:
            return None
        
        df = pd.DataFrame([asdict(e) for e in recent_events])
        
        # Create figure
        plt.figure(figsize=(12, 6))
        
        # Plot events by day
        daily_events = df.groupby(df['timestamp'].dt.date).size()
        sns.lineplot(data=daily_events, marker='o')
        
        plt.title('Bot Usage Over Time')
        plt.xlabel('Date')
        plt.ylabel('Number of Events')
        plt.xticks(rotation=45)
        
        # Save plot to BytesIO
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        
        buf.seek(0)
        return buf
    
    def generate_user_activity_graph(self, user_id: str, days: int = 30) -> BytesIO:
        """Generate a graph showing user activity over time.
        
        Args:
            user_id: ID of the user to analyze
            days: Number of days to analyze
            
        Returns:
            BytesIO object containing the graph image
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        user_events = [e for e in self.events if e.user_id == user_id and e.timestamp >= cutoff_date]
        
        if not user_events:
            return None
        
        df = pd.DataFrame([asdict(e) for e in user_events])
        
        # Create figure
        plt.figure(figsize=(12, 6))
        
        # Plot events by day
        daily_events = df.groupby(df['timestamp'].dt.date).size()
        sns.lineplot(data=daily_events, marker='o')
        
        plt.title('User Activity Over Time')
        plt.xlabel('Date')
        plt.ylabel('Number of Events')
        plt.xticks(rotation=45)
        
        # Save plot to BytesIO
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        
        buf.seek(0)
        return buf
    
    def generate_command_usage_graph(self, days: int = 30) -> BytesIO:
        """Generate a graph showing command usage distribution.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            BytesIO object containing the graph image
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        command_events = [e for e in self.events if e.event_type == 'command_used' and e.timestamp >= cutoff_date]
        
        if not command_events:
            return None
        
        df = pd.DataFrame([asdict(e) for e in command_events])
        
        # Get command usage counts
        command_counts = df['data'].apply(lambda x: x.get('command', 'unknown')).value_counts()
        
        # Create figure
        plt.figure(figsize=(12, 6))
        
        # Plot command usage
        sns.barplot(x=command_counts.values, y=command_counts.index)
        
        plt.title('Command Usage Distribution')
        plt.xlabel('Number of Uses')
        plt.ylabel('Command')
        
        # Save plot to BytesIO
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        plt.close()
        
        buf.seek(0)
        return buf
    
    def initialize_guild(self, guild_id: str) -> bool:
        """Initialize analytics data for a new guild.
        
        Args:
            guild_id: The Discord guild ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            guild_file = os.path.join(self.guild_data_dir, f"{guild_id}.json")
            
            # Check if guild data already exists
            if os.path.exists(guild_file):
                return True
                
            # Create initial guild data
            guild_data = {
                "guild_id": guild_id,
                "created_at": datetime.utcnow().isoformat(),
                "total_events": 0,
                "unique_users": [],
                "events_by_type": {},
                "events_by_hour": {str(i): 0 for i in range(24)},
                "events_by_day": {},
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Save guild data
            with open(guild_file, 'w') as f:
                json.dump(guild_data, f, indent=2)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing guild {guild_id}: {e}")
            return False 