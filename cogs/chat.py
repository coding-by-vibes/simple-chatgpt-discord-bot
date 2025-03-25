import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from utils.error_handler import ErrorHandler
from utils.conversation_manager import ConversationManager
from utils.conversation_analyzer import ConversationAnalyzer
from utils.ui_components import UIComponents
import logging

class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.error_handler = bot.error_handler
        self.conversation_manager = bot.conversation_manager
        self.conversation_analyzer = bot.conversation_analyzer
        self.ui_components = bot.ui_components
        self.logger = logging.getLogger(__name__)

    @app_commands.command(
        name="ask",
        description="Ask a question or have a conversation with the AI"
    )
    @app_commands.describe(
        question="Your question or message for the AI"
    )
    async def ask(
        self,
        interaction: discord.Interaction,
        question: str
    ):
        """
        Have a conversation with the AI assistant.
        
        Parameters:
        -----------
        question: str
            The question or message for the AI
        """
        await interaction.response.defer()

        try:
            # Get conversation history
            conversation = self.conversation_manager.get_conversation(interaction.guild_id)
            
            # Add user's message to history
            self.conversation_manager.add_message(
                guild_id=interaction.guild_id,
                role="user",
                content=question
            )

            # Generate AI response
            response = await self.conversation_manager.generate_response(
                guild_id=interaction.guild_id,
                user_id=str(interaction.user.id),
                message=question
            )

            # Add AI response to history
            self.conversation_manager.add_message(
                guild_id=interaction.guild_id,
                role="assistant",
                content=response
            )

            # Split response if too long
            if len(response) > 2000:
                chunks = [response[i:i + 1990] for i in range(0, len(response), 1990)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await interaction.followup.send(chunk)
                    else:
                        await interaction.channel.send(chunk)
            else:
                await interaction.followup.send(response)

            # Track interaction with analytics
            interaction_data = {
                "command": "ask",
                "content_length": len(question),
                "response_length": len(response),
                "guild_id": str(interaction.guild_id)
            }
            self.bot.user_analytics.track_interaction(str(interaction.user.id), interaction_data)

        except Exception as e:
            error_id = self.error_handler.log_error(
                error=e,
                context={
                    "command": "ask",
                    "user_id": str(interaction.user.id),
                    "guild_id": str(interaction.guild_id)
                }
            )
            await interaction.followup.send(
                embed=self.ui_components.create_error_embed(
                    error=e,
                    error_id=error_id,
                    context={"command": "ask"}
                )
            )

async def setup(bot):
    await bot.add_cog(Chat(bot)) 