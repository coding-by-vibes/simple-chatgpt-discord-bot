from typing import Dict, List, Optional, Union
import os
import re
from datetime import datetime
import logging
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import openai
from .recipe_manager import RecipeManager

class YouTubeManager:
    def __init__(self, api_key: str):
        """Initialize the YouTube manager.
        
        Args:
            api_key: YouTube API key
        """
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.logger = logging.getLogger(__name__)
        self.recipe_manager = RecipeManager()
        self.formatter = TextFormatter()
        
        # Configure logger to handle Unicode
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setStream(open(handler.stream.fileno(), mode=handler.stream.mode, encoding='utf-8'))
            elif isinstance(handler, logging.FileHandler):
                handler.setStream(open(handler.baseFilename, mode=handler.mode, encoding='utf-8'))
        
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats.
        
        Args:
            url: YouTube video URL
            
        Returns:
            str: Video ID if found, None otherwise
        """
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu.be\/|youtube.com\/embed\/)([^&\n?#]+)',
            r'youtube.com\/shorts\/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    async def get_video_details(self, url: str) -> Dict:
        """Get video details from YouTube API."""
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")

            # Get video details from YouTube API
            try:
                request = self.youtube.videos().list(
                    part="snippet,contentDetails,statistics",
                    id=video_id
                )
                response = request.execute()
            except Exception as e:
                self.logger.error(f"YouTube API error: {str(e)}")
                raise ValueError(f"Failed to fetch video details: {str(e)}")

            if not response.get('items'):
                raise ValueError("Video not found or not accessible")

            video = response['items'][0]
            
            return {
                'title': video['snippet']['title'],
                'channel': video['snippet']['channelTitle'],
                'duration': video['contentDetails']['duration'],
                'views': int(video['statistics']['viewCount']),
                'thumbnail': video['snippet']['thumbnails']['high']['url'] if 'thumbnails' in video['snippet'] else None
            }
        except Exception as e:
            self.logger.error(f"Error getting video details: {str(e)}")
            raise
    
    async def get_transcript(self, url: str, detailed: bool = False) -> Optional[str]:
        """Get transcript from YouTube video."""
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                return None

            # Get transcript list
            transcript_list = YouTubeTranscriptApi.list_transcripts(self.youtube, video_id)
            
            # Try to get manual English transcript first
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
            except:
                # If no manual transcript, try auto-generated English
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except:
                    self.logger.error(f"No English transcript found for video {video_id}")
                    return None

            # Get transcript
            transcript_data = transcript.fetch()
            formatted_transcript = self.formatter.format_transcript(transcript_data)
            
            # Check if transcript contains a recipe
            if self.recipe_manager.is_recipe_content(formatted_transcript):
                recipe = self.recipe_manager.extract_recipe(formatted_transcript, url)
                if recipe:
                    recipe_cards = self.recipe_manager.format_recipe_card(recipe)
                    # Join all cards with newlines since this method expects a single string
                    return "\n\n".join(recipe_cards)
            
            # If no recipe found, return regular transcript
            return formatted_transcript

        except Exception as e:
            self.logger.error(f"Error getting transcript: {str(e)}")
            return None
    
    def format_duration(self, duration: str) -> str:
        """Convert YouTube duration format to readable format.
        
        Args:
            duration: Duration in YouTube format (PT1H2M10S)
            
        Returns:
            str: Formatted duration string
        """
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match:
            return "Unknown duration"
            
        hours, minutes, seconds = match.groups()
        parts = []
        
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if seconds:
            parts.append(f"{seconds}s")
            
        return " ".join(parts)
    
    async def create_summary(self, transcript: str, video_details: Dict, detailed: bool) -> str:
        """Generate a summary of the video using OpenAI's API."""
        try:
            # Create prompt based on detail level
            if detailed:
                prompt = (
                    f"Please provide a detailed summary of this video titled '{video_details['title']}' "
                    f"by {video_details['channel']}. Include key points with their timestamps:\n\n{transcript}"
                )
            else:
                prompt = (
                    f"Please provide a concise summary of this video titled '{video_details['title']}' "
                    f"by {video_details['channel']}. Focus on the main points:\n\n{transcript}"
                )

            # Get summary from OpenAI
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that creates clear and informative video summaries."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            self.logger.error(f"Error creating summary: {str(e)}")
            raise

    def is_recipe_video(self, url: str) -> bool:
        """Check if video likely contains a recipe based on title and description."""
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                return False

            # Get video info
            video_info = self.get_video_details(url)
            if not video_info:
                return False

            # Check title for recipe indicators
            title = video_info['title'].lower()
            recipe_indicators = [
                'recipe', 'cooking', 'baking', 'how to make', 'how to cook',
                'tutorial', 'guide', 'step by step', 'ingredients', 'instructions'
            ]
            
            return any(indicator in title for indicator in recipe_indicators)

        except Exception as e:
            self.logger.error(f"Error checking if recipe video: {str(e)}")
            return False 