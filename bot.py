import discord
from discord.ext import commands
import os
from pathlib import Path
from dotenv import load_dotenv
from settings.settings_manager import SettingsManager
from settings.conversation_manager import ConversationManager
from settings.conversation_analyzer import ConversationAnalyzer
from settings.user_manager import UserManager
from utils.article_summarizer import ArticleSummarizer
from utils.feedback_manager import FeedbackManager
from utils.error_handler import ErrorHandler
from utils.persona_recommender import PersonaRecommender
from utils.correction_manager import CorrectionManager
from utils.conversation_enhancer import ConversationEnhancer
from utils.user_analytics import UserAnalytics
from utils.ui_components import UIComponents
from utils.analytics_manager import AnalyticsManager
from utils.security_manager import SecurityManager
from utils.cache_manager import CacheManager
from utils.rate_limiter import RateLimiter
from utils.response_manager import ResponseManager
from utils.youtube_manager import YouTubeManager
from utils.rbac_manager import RBACManager
from datetime import datetime
from discord.ext import commands
from discord import app_commands

# Load environment variables
load_dotenv()

# Verify environment variables are loaded
required_env_vars = {
    'DISCORD_BOT_TOKEN': "Discord bot token not found in environment variables.",
    'OPENAI_API_KEY': "OpenAI API key not found in environment variables.",
    'YOUTUBE_API_KEY': "YouTube API key not found in environment variables."
}

for var, message in required_env_vars.items():
    if not os.getenv(var):
        raise ValueError(f"{message} Please check your .env file.")

class ChatGPTBot(commands.Bot):
    def __init__(self):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True  # Add guilds intent for better server management
        
        super().__init__(
            command_prefix='!',  # Fallback prefix for message commands
            intents=intents,
            help_command=None,  # Disable default help command
            case_insensitive=True  # Make commands case-insensitive
        )
        
        # Initialize settings directory
        self.settings_dir = os.path.join(os.path.dirname(__file__), 'settings')
        os.makedirs(self.settings_dir, exist_ok=True)
        
        # Create Path object for settings dir
        self.settings_path = Path(self.settings_dir)
        
        # Initialize managers
        self.init_managers()
        
    def init_managers(self):
        """Initialize all manager instances."""
        try:
            # Initialize settings and core managers
            self.settings_manager = SettingsManager(self.settings_dir)
            self.error_handler = ErrorHandler(self.settings_dir)
            self.cache_manager = CacheManager(self.settings_dir)
            self.security_manager = SecurityManager(self.settings_dir)
            self.rate_limiter = RateLimiter(self.settings_dir)
            self.rbac_manager = RBACManager(self.settings_dir)
            
            # Initialize conversation and user managers
            self.conversation_manager = ConversationManager(self.settings_dir)
            self.conversation_analyzer = ConversationAnalyzer(self.settings_path)
            self.conversation_enhancer = ConversationEnhancer(self.settings_dir)
            self.user_manager = UserManager(self.settings_dir)
            self.user_analytics = UserAnalytics(self.settings_dir)
            
            # Initialize feature managers
            self.article_summarizer = ArticleSummarizer()
            self.feedback_manager = FeedbackManager(self.settings_dir)
            self.persona_recommender = PersonaRecommender(self.settings_dir)
            self.correction_manager = CorrectionManager(self.settings_dir)
            self.analytics_manager = AnalyticsManager(self.settings_dir)
            self.response_manager = ResponseManager()
            self.ui_components = UIComponents()
            
            # Initialize API-dependent managers
            youtube_api_key = os.getenv('YOUTUBE_API_KEY')
            if not youtube_api_key:
                raise ValueError("YouTube API key not found in environment variables")
            self.youtube_manager = YouTubeManager(youtube_api_key)
            
        except Exception as e:
            error_id = self.error_handler.log_error(
                error=e,
                command="init_managers",
                severity="HIGH",
                context={"phase": "initialization"}
            )
            raise RuntimeError(f"Failed to initialize managers: {e} (Error ID: {error_id})")
        
    async def setup_hook(self):
        """Set up bot cogs and start tasks."""
        try:
            # Load cogs
            cogs = [
                "cogs.admin",
                "cogs.user",
                "cogs.analytics",
                "cogs.conversation",
                "cogs.media",
                "cogs.chat"
            ]
            
            for cog in cogs:
                try:
                    await self.load_extension(cog)
                except Exception as e:
                    error_id = self.error_handler.log_error(
                        error=e,
                        command="setup_hook",
                        severity="MEDIUM",
                        context={"cog": cog}
                    )
                    print(f"Failed to load cog {cog}: {e} (Error ID: {error_id})")
                    
        except Exception as e:
            error_id = self.error_handler.log_error(
                error=e,
                command="setup_hook",
                severity="HIGH",
                context={"phase": "cog_loading"}
            )
            raise RuntimeError(f"Failed to set up bot: {e} (Error ID: {error_id})")
        
    async def on_ready(self):
        """Called when bot is ready."""
        print(f'Bot is ready! Logged in as {self.user.name}')
        print(f'Connected to {len(self.guilds)} guilds')
        print(f'Bot ID: {self.user.id}')
        print(f'Discord.py version: {discord.__version__}')
        
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
            
            # Initialize analytics for all connected guilds
            for guild in self.guilds:
                self.analytics_manager.initialize_guild(str(guild.id))
                
        except Exception as e:
            error_id = self.error_handler.log_error(
                error=e,
                context={
                    "action": "syncing_commands",
                    "phase": "on_ready"
                }
            )
            print(f"Failed to sync commands: {e} (Error ID: {error_id})")

    async def on_message(self, message: discord.Message):
        """Handle message events."""
        try:
            # Ignore messages from the bot itself
            if message.author == self.user:
                return

            # Process commands first
            await self.process_commands(message)

            # Check if the message is a reply to the bot
            if message.reference and message.reference.resolved:
                referenced_message = message.reference.resolved
                if referenced_message.author == self.user:
                    # Check rate limits before processing
                    if not self.rate_limiter.check_rate_limit(str(message.author.id), "message_reply"):
                        await message.channel.send(
                            embed=self.ui_components.create_error_embed(
                                error="Rate limit exceeded. Please wait before sending more messages.",
                                context={"command": "message_reply"}
                            )
                        )
                        return

                    # Defer response with typing indicator
                    async with message.channel.typing():
                        # Add user's message to conversation
                        success = self.conversation_manager.add_message(
                            guild_id=message.guild.id,
                            role="user",
                            content=message.content
                        )
                        
                        if not success:
                            raise Exception("Failed to add user message to conversation")

                        # Generate response
                        response = await self.conversation_manager.generate_response(
                            guild_id=message.guild.id,
                            user_id=str(message.author.id),
                            message=message.content
                        )

                        if not response:
                            raise Exception("Failed to generate response")

                        # Add bot's response to conversation
                        success = self.conversation_manager.add_message(
                            guild_id=message.guild.id,
                            role="assistant",
                            content=response
                        )
                        
                        if not success:
                            raise Exception("Failed to add bot response to conversation")

                        # Split response if too long
                        if len(response) > 2000:
                            chunks = [response[i:i + 1990] for i in range(0, len(response), 1990)]
                            for chunk in chunks:
                                await message.channel.send(chunk)
                        else:
                            await message.channel.send(response)

                        # Track interaction
                        interaction_data = {
                            "type": "reply",
                            "content_length": len(message.content),
                            "response_length": len(response),
                            "guild_id": str(message.guild.id),
                            "timestamp": datetime.now().isoformat()
                        }
                        self.user_analytics.track_interaction(str(message.author.id), interaction_data)

        except discord.Forbidden as e:
            error_id = self.error_handler.log_error(
                error=e,
                command="message_reply",
                severity="HIGH",
                context={
                    "user_id": str(message.author.id),
                    "guild_id": str(message.guild.id),
                    "error_type": "permission_error"
                }
            )
            # Don't send error message if we don't have permission
            print(f"Permission error in message_reply: {e} (Error ID: {error_id})")
            
        except Exception as e:
            error_id = self.error_handler.log_error(
                error=e,
                command="message_reply",
                severity="MEDIUM",
                context={
                    "user_id": str(message.author.id),
                    "guild_id": str(message.guild.id),
                    "error_type": "general_error"
                }
            )
            try:
                await message.channel.send(
                    embed=self.ui_components.create_error_embed(
                        error=e,
                        error_id=error_id,
                        context={"command": "message_reply"}
                    )
                )
            except discord.Forbidden:
                print(f"Could not send error message: {e} (Error ID: {error_id})")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle application command errors."""
        try:
            if isinstance(error, app_commands.CommandOnCooldown):
                # Handle rate limiting
                error_id = self.error_handler.log_error(
                    error=error,
                    command=interaction.command.name,
                    severity="LOW",
                    context={
                        "user_id": str(interaction.user.id),
                        "guild_id": str(interaction.guild_id) if interaction.guild_id else "DM",
                        "retry_after": error.retry_after
                    }
                )
                
                # Create a more informative error message
                embed = discord.Embed(
                    title="Rate Limited",
                    description=f"This command is on cooldown. Please try again in {error.retry_after:.1f} seconds.",
                    color=discord.Color.orange()
                )
                embed.add_field(name="Command", value=interaction.command.name)
                embed.add_field(name="Error ID", value=error_id)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            elif isinstance(error, app_commands.MissingPermissions):
                # Handle permission errors
                error_id = self.error_handler.log_error(
                    error=error,
                    command=interaction.command.name,
                    severity="MEDIUM",
                    context={
                        "user_id": str(interaction.user.id),
                        "guild_id": str(interaction.guild_id) if interaction.guild_id else "DM",
                        "missing_permissions": error.missing_permissions
                    }
                )
                
                embed = discord.Embed(
                    title="Missing Permissions",
                    description="You don't have permission to use this command.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Required Permissions", value=", ".join(error.missing_permissions))
                embed.add_field(name="Error ID", value=error_id)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            else:
                # Handle other errors
                error_id = self.error_handler.log_error(
                    error=error,
                    command=interaction.command.name,
                    severity="HIGH",
                    context={
                        "user_id": str(interaction.user.id),
                        "guild_id": str(interaction.guild_id) if interaction.guild_id else "DM"
                    }
                )
                
                embed = discord.Embed(
                    title="Error",
                    description="An error occurred while processing your command.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Error ID", value=error_id)
                
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    
        except Exception as e:
            # Log any errors in the error handler itself
            print(f"Error in error handler: {e}")
            
    def check_rate_limit(self, interaction: discord.Interaction, command_name: str) -> bool:
        """Check if a command is rate limited."""
        try:
            # Get user and guild IDs
            user_id = str(interaction.user.id)
            guild_id = str(interaction.guild_id) if interaction.guild_id else "DM"
            
            # Check rate limits
            if not self.rate_limiter.check_rate_limit(user_id, command_name):
                # Log rate limit hit
                self.error_handler.log_error(
                    error=app_commands.CommandOnCooldown(command_name, 0),
                    command=command_name,
                    severity="LOW",
                    context={
                        "user_id": user_id,
                        "guild_id": guild_id,
                        "type": "rate_limit"
                    }
                )
                return False
                
            # Update rate limit counters
            self.rate_limiter.update_rate_limit(user_id, command_name)
            return True
            
        except Exception as e:
            # Log any errors in rate limiting
            self.error_handler.log_error(
                error=e,
                command=command_name,
                severity="MEDIUM",
                context={
                    "user_id": str(interaction.user.id),
                    "guild_id": str(interaction.guild_id) if interaction.guild_id else "DM",
                    "type": "rate_limit_check"
                }
            )
            return True  # Allow command to proceed if rate limiting fails

def main():
    """Run the bot."""
    bot = ChatGPTBot()
    bot.run(os.getenv('DISCORD_BOT_TOKEN'))

if __name__ == "__main__":
    main() 