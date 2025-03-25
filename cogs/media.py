import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from utils.error_handler import ErrorHandler
from utils.youtube_manager import YouTubeManager
from utils.article_summarizer import ArticleSummarizer
from utils.ui_components import UIComponents
import logging

class Media(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.error_handler = bot.error_handler
        self.youtube_manager = bot.youtube_manager
        self.article_summarizer = bot.article_summarizer
        self.ui_components = bot.ui_components
        self.logger = logging.getLogger(__name__)

    @app_commands.command(
        name="summarize",
        description="Summarize content from a URL (supports articles and YouTube videos)"
    )
    @app_commands.describe(
        url="The URL of the content to summarize",
        summary_type="Type of summary to generate"
    )
    @app_commands.choices(summary_type=[
        app_commands.Choice(name="Default", value="default"),
        app_commands.Choice(name="TL;DR (Very Brief)", value="tldr"),
        app_commands.Choice(name="Detailed", value="detailed")
    ])
    async def summarize(
        self,
        interaction: discord.Interaction,
        url: str,
        summary_type: str = "default"
    ):
        """
        Summarize content from a URL. Automatically detects if it's an article or YouTube video.
        
        Parameters:
        -----------
        url: str
            The URL of the content to summarize
        summary_type: str
            Type of summary to generate (default, tldr, or detailed)
        """
        await interaction.response.defer()

        try:
            # First, try to detect if it's a YouTube video
            video_id = self.youtube_manager.extract_video_id(url)
            
            if video_id:
                self.logger.info(f"Processing YouTube video with ID: {video_id}")
                try:
                    # Handle YouTube video
                    video_details = await self.youtube_manager.get_video_details(url)
                    self.logger.info(f"Successfully fetched video details: {video_details}")
                except ValueError as ve:
                    error_msg = str(ve)
                    self.logger.error(f"YouTube API error: {error_msg}")
                    if error_msg == "Video not found or not accessible":
                        await interaction.followup.send(
                            "❌ Could not access this video.\n\n"
                            "This can happen when:\n"
                            "• The video is private or unlisted\n"
                            "• The video has been deleted\n"
                            "• The video is region-restricted\n"
                            "• The video URL is incorrect\n\n"
                            "Please check if you can access the video in your browser and try again."
                        )
                        return
                    raise ve

                self.logger.info("Fetching video transcript...")
                # Use detailed timestamps for detailed summaries
                transcript = await self.youtube_manager.get_transcript(url, detailed=(summary_type == "detailed"))
                
                if not transcript:
                    error_msg = (
                        "❌ Could not find a transcript for this video.\n\n"
                        "This can happen when:\n"
                        "• The video doesn't have closed captions/subtitles\n"
                        "• Auto-generated captions are not available\n"
                        "• Captions are disabled by the video owner\n\n"
                        "Try:\n"
                        "1. Check if the video has captions by looking for the CC button in YouTube\n"
                        "2. Try another video that has captions enabled\n"
                        "3. Try summarizing an article instead\n\n"
                        "Note: Some videos may have captions in languages other than English, "
                        "which are not currently supported."
                    )
                    await interaction.followup.send(error_msg)
                    return
                    
                # Create embed for video information
                embed = discord.Embed(
                    title=f"📺 {video_details['title']}",
                    url=url,
                    description=f"Channel: {video_details['channel']}\nDuration: {video_details['duration']}\nViews: {video_details['views']:,}",
                    color=discord.Color.red()
                )
                
                if video_details.get('thumbnail'):
                    embed.set_thumbnail(url=video_details['thumbnail'])
                    
                # Send video information
                await interaction.followup.send(embed=embed)
                
                # Generate and send summary
                summary = await self.youtube_manager.create_summary(transcript, video_details, summary_type == "detailed")
                
                # Split summary into chunks if needed (Discord has a 2000 character limit)
                chunks = [summary[i:i + 1990] for i in range(0, len(summary), 1990)]
                
                for chunk in chunks:
                    await interaction.followup.send(f"```{chunk}```")
            
            else:
                # Handle article
                summary_data = self.article_summarizer.summarize_article(url, summary_type=summary_type)
                
                if not summary_data:
                    await interaction.followup.send("❌ Could not summarize the content. Please check if the URL is valid and accessible.")
                    return

                # Format and send the summary
                summary_text = self.article_summarizer.format_summary(summary_data)
                
                # Split long messages if needed
                if len(summary_text) > 2000:
                    parts = [summary_text[i:i+1900] for i in range(0, len(summary_text), 1900)]
                    for i, part in enumerate(parts):
                        if i == 0:
                            await interaction.followup.send(part)
                        else:
                            await interaction.channel.send(part)
                else:
                    await interaction.followup.send(summary_text)

            # Track interaction with analytics
            interaction_data = {
                "command": "summarize",
                "content_type": "video" if video_id else "article",
                "url": url,
                "summary_type": summary_type,
                "guild_id": str(interaction.guild_id)
            }
            self.bot.user_analytics.track_interaction(str(interaction.user.id), interaction_data)

        except Exception as e:
            error_id = self.error_handler.log_error(
                error=e,
                context={
                    "command": "summarize",
                    "user_id": str(interaction.user.id),
                    "guild_id": str(interaction.guild_id)
                }
            )
            await interaction.followup.send(
                f"❌ An error occurred while processing your request. Error ID: {error_id}"
            )

async def setup(bot):
    await bot.add_cog(Media(bot)) 