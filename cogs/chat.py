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
            success = self.conversation_manager.add_message(
                user_id=str(interaction.user.id),
                role="user",
                content=question,
                channel_id=str(interaction.channel_id)
            )
            
            if not success:
                raise Exception("Failed to add user message to conversation")

            # Show user's question
            await interaction.followup.send(f"**{interaction.user.name}:** {question}")

            # Generate AI response
            response = await self.conversation_manager.generate_response(
                user_id=str(interaction.user.id),
                message=question,
                channel_id=str(interaction.channel_id)
            )

            if not response:
                raise Exception("Failed to generate response")

            # Add AI response to history
            success = self.conversation_manager.add_message(
                user_id=str(interaction.user.id),
                role="assistant",
                content=response,
                channel_id=str(interaction.channel_id)
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

    @app_commands.command(
        name="wiki",
        description="Get Wikipedia-based answers to your questions"
    )
    @app_commands.describe(
        query="Your question or topic to search on Wikipedia"
    )
    async def wiki(
        self,
        interaction: discord.Interaction,
        query: str
    ):
        """
        Get Wikipedia-based answers to your questions.
        
        Parameters:
        -----------
        query: str
            The question or topic to search on Wikipedia
        """
        await interaction.response.defer()

        try:
            # Show user's query
            await interaction.followup.send(f"**{interaction.user.name}:** {query}")

            # Get Wikipedia summary
            summary, url = self.bot.article_summarizer.get_wikipedia_summary(query)
            
            if not summary:
                await interaction.followup.send(
                    embed=self.ui_components.create_error_embed(
                        error=url,  # url contains error message in this case
                        context={"command": "wiki"}
                    )
                )
                return

            # Create embed for response
            embed = discord.Embed(
                title="📚 Wikipedia Summary",
                description=summary,
                url=url,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Source: Wikipedia")

            # Send response
            await interaction.followup.send(embed=embed)

            # Track interaction with analytics
            interaction_data = {
                "command": "wiki",
                "content_length": len(query),
                "response_length": len(summary),
                "guild_id": str(interaction.guild_id)
            }
            self.bot.user_analytics.track_interaction(str(interaction.user.id), interaction_data)

        except Exception as e:
            error_id = self.error_handler.log_error(
                error=e,
                context={
                    "command": "wiki",
                    "user_id": str(interaction.user.id),
                    "guild_id": str(interaction.guild_id)
                }
            )
            await interaction.followup.send(
                embed=self.ui_components.create_error_embed(
                    error=e,
                    error_id=error_id,
                    context={"command": "wiki"}
                )
            )

async def setup(bot):
    await bot.add_cog(Chat(bot)) 