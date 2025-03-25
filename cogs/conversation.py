import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from utils.error_handler import ErrorHandler
from utils.conversation_manager import ConversationManager
from utils.conversation_analyzer import ConversationAnalyzer
from utils.conversation_enhancer import ConversationEnhancer
from utils.ui_components import UIComponents
from datetime import datetime

class Conversation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.error_handler = bot.error_handler
        self.conversation_manager = bot.conversation_manager
        self.conversation_analyzer = bot.conversation_analyzer
        self.conversation_enhancer = bot.conversation_enhancer
        self.ui_components = bot.ui_components

    @app_commands.command(name="clearconversation", description="Clear the current conversation history")
    async def clearconversation(self, interaction: discord.Interaction):
        """Clear the current conversation history."""
        await interaction.response.defer()

        try:
            self.conversation_manager.clear_conversation(interaction.guild_id)
            await interaction.followup.send("✅ Conversation history cleared!")
        except Exception as e:
            await interaction.followup.send(f"❌ Error clearing conversation: {str(e)}")

    @app_commands.command(name="conversation_stats", description="View conversation statistics")
    async def conversation_stats(self, interaction: discord.Interaction):
        """View conversation statistics."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get conversation statistics
            stats = self.conversation_manager.get_conversation_stats()
            
            # Create embed with statistics
            embed = self.ui_components.create_embed(
                title="📊 Conversation Statistics",
                description="Current conversation statistics:",
                color=discord.Color.blue(),
                fields=[
                    {
                        "name": "Overview",
                        "value": f"""
Total Messages: {stats['total_messages']}
Unique Participants: {stats['unique_participants']}
Average Message Length: {stats['avg_message_length']:.1f} characters
Duration: {stats['duration']}
                        """,
                        "inline": False
                    },
                    {
                        "name": "Message Distribution",
                        "value": "\n".join(f"- {role}: {count}" for role, count in stats['message_distribution'].items()),
                        "inline": False
                    },
                    {
                        "name": "Current Topic",
                        "value": stats['current_topic'] or "No topic detected",
                        "inline": False
                    },
                    {
                        "name": "Overall Sentiment",
                        "value": stats['overall_sentiment'],
                        "inline": False
                    }
                ],
                footer_text=f"Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="conversation_stats",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                embed=self.ui_components.create_error_embed(
                    error=e,
                    error_id=error_id,
                    context={"command": "conversation_stats"}
                ),
                ephemeral=True
            )

    @app_commands.command(name="conversation_settings", description="View or update conversation settings")
    async def conversation_settings(self, interaction: discord.Interaction, 
                                max_history: Optional[int] = None,
                                context_window: Optional[int] = None,
                                auto_summarize: Optional[bool] = None):
        """View or update conversation settings."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get current conversation
            conversation = self.conversation_manager.get_conversation(str(interaction.guild_id))
            if not conversation:
                conversation = self.conversation_manager.create_conversation(str(interaction.guild_id))
            
            # Get current settings
            current_settings = conversation.metadata["settings"]
            
            # Update settings if provided
            if any([max_history, context_window, auto_summarize is not None]):
                new_settings = {}
                if max_history is not None:
                    new_settings["max_history"] = max_history
                if context_window is not None:
                    new_settings["context_window"] = context_window
                if auto_summarize is not None:
                    new_settings["auto_summarize"] = auto_summarize
                
                # Update settings
                success = self.conversation_manager.update_conversation_settings(
                    str(interaction.guild_id),
                    new_settings
                )
                
                if not success:
                    await interaction.followup.send(
                        "❌ Error updating conversation settings.",
                        ephemeral=True
                    )
                    return
            
            # Format response
            response = "**⚙️ Conversation Settings**\n\n"
            response += f"**Max History:** {current_settings['max_history']} messages\n"
            response += f"**Context Window:** {current_settings['context_window']} messages\n"
            response += f"**Auto Summarize:** {'Enabled' if current_settings['auto_summarize'] else 'Disabled'}\n"
            response += f"**Topic Detection:** {'Enabled' if current_settings['topic_detection'] else 'Disabled'}\n"
            response += f"**Sentiment Tracking:** {'Enabled' if current_settings['sentiment_tracking'] else 'Disabled'}\n\n"
            
            response += "To update settings, use:\n"
            response += "`/conversation_settings [max_history] [context_window] [auto_summarize]`"
            
            await interaction.followup.send(response, ephemeral=True)
            
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="conversation_settings",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                f"❌ Error managing conversation settings: {str(e)} (Error ID: {error_id})",
                ephemeral=True
            )

    @app_commands.command(name="delete_conversation", description="Delete the current conversation (Admin only)")
    async def delete_conversation(self, interaction: discord.Interaction):
        """Delete the current conversation."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user has admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send(
                    "❌ You need administrator permissions to delete conversations.",
                    ephemeral=True
                )
                return
            
            # Delete conversation
            success = self.conversation_manager.delete_conversation(str(interaction.guild_id))
            
            if success:
                await interaction.followup.send(
                    "✅ Conversation deleted successfully!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Error deleting conversation.",
                    ephemeral=True
                )
            
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="delete_conversation",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                f"❌ Error deleting conversation: {str(e)} (Error ID: {error_id})",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Conversation(bot)) 