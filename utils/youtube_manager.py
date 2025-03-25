from typing import Dict, List, Optional, Union
import os
import re
from datetime import datetime
import logging
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import openai

class YouTubeManager:
    def __init__(self, api_key: str):
        """Initialize the YouTube manager with API credentials."""
        if not api_key:
            raise ValueError("YouTube API key is required")
        self.api_key = api_key
        try:
            self.youtube = build('youtube', 'v3', developerKey=api_key)
        except Exception as e:
            raise ValueError(f"Failed to initialize YouTube API client: {str(e)}")
        self.logger = logging.getLogger(__name__)
        
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
        """Get video transcript with timestamps."""
        try:
            video_id = self.extract_video_id(url)
            if not video_id:
                self.logger.error("Failed to extract video ID from URL")
                return None

            # Get available transcripts
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                self.logger.info(f"Available transcripts: {transcript_list}")
            except Exception as e:
                self.logger.error(f"Failed to list transcripts: {str(e)}")
                return None
            
            # Try to get English transcript, fall back to auto-translated if needed
            transcript = None
            errors = []
            
            # Try manual transcripts first
            for lang in ['en', 'en-US', 'en-GB']:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    self.logger.info(f"Found manual transcript in {lang}")
                    break
                except Exception as e:
                    errors.append(f"No manual {lang} transcript: {str(e)}")
            
            # If no manual transcript, try auto-generated
            if not transcript:
                try:
                    transcript = transcript_list.find_generated_transcript()
                    self.logger.info("Found auto-generated transcript")
                except Exception as e:
                    errors.append(f"No auto-generated transcript: {str(e)}")
                    self.logger.error(f"Failed to get any transcript. Errors: {'; '.join(errors)}")
                    return None

            # Get the transcript data
            try:
                transcript_data = transcript.fetch()
                self.logger.info(f"Successfully fetched transcript with {len(transcript_data)} entries")
                
                # Format transcript based on detail level
                if detailed:
                    # Include timestamps for detailed view
                    formatted_transcript = []
                    for entry in transcript_data:
                        # Access attributes directly from the TranscriptEntry object
                        timestamp = int(float(entry.start))
                        minutes = timestamp // 60
                        seconds = timestamp % 60
                        formatted_transcript.append(f"[{minutes:02d}:{seconds:02d}] {entry.text}")
                    return "\n".join(formatted_transcript)
                else:
                    # Simple concatenation for basic view
                    return " ".join(entry.text for entry in transcript_data)
                    
            except Exception as e:
                self.logger.error(f"Failed to fetch or format transcript data: {str(e)}")
                return None

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