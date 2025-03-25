import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from utils.error_handler import ErrorHandler
from utils.user_manager import UserManager
from utils.persona_recommender import PersonaRecommender
from utils.ui_components import UIComponents

class PersonaSelect(discord.ui.Select):
    def __init__(self, personas: list[str], user_id: str):
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label=persona,
                description=f"Switch to {persona} persona",
                value=persona
            ) for persona in personas
        ]
        super().__init__(
            placeholder="Choose a persona...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_persona = self.values[0]
        self.view.user_manager.set_user_preferred_persona(self.user_id, selected_persona)
        await interaction.response.send_message(
            f"✅ Your preferred persona has been set to: **{selected_persona}**",
            ephemeral=True
        )

class PersonaView(discord.ui.View):
    def __init__(self, personas: list[str], user_id: str, user_manager: UserManager):
        super().__init__()
        self.user_manager = user_manager
        self.add_item(PersonaSelect(personas, user_id))

class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.error_handler = bot.error_handler
        self.user_manager = bot.user_manager
        self.persona_recommender = bot.persona_recommender
        self.ui_components = bot.ui_components

    @app_commands.command(name="bespoke", description="Create a personalized AI assistant for yourself")
    async def bespoke(self, interaction: discord.Interaction):
        """Create a personalized AI assistant for yourself."""
        await interaction.response.defer()

        try:
            # Check if user already has a bespoke persona
            existing_persona = self.user_manager.get_bespoke_persona(str(interaction.user.id))
            if existing_persona:
                await interaction.followup.send("❌ You already have a bespoke persona! Use `/bespoke_stats` to view your persona's stats.")
                return

            # Create new bespoke persona
            persona = self.user_manager.create_bespoke_persona(str(interaction.user.id))
            
            response = (
                "✅ Your bespoke persona has been created!\n\n"
                "Your AI assistant will now learn from your interactions and adapt to your preferences.\n"
                "You can:\n"
                "- Use `/bespoke_stats` to view your persona's stats\n"
                "- Use `/setpersona` to switch to your bespoke persona\n"
                "- Just chat with me to help shape your persona!"
            )
            
            await interaction.followup.send(response)
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating bespoke persona: {str(e)}")

    @app_commands.command(name="bespoke_stats", description="View your bespoke persona's statistics")
    async def bespoke_stats(self, interaction: discord.Interaction):
        """View your bespoke persona's statistics."""
        await interaction.response.defer()

        try:
            stats = self.user_manager.get_user_interaction_stats(str(interaction.user.id))
            if not stats:
                await interaction.followup.send("❌ You don't have a bespoke persona yet! Use `/bespoke` to create one.")
                return

            response = (
                "**Your Bespoke Persona Stats:**\n"
                f"- Total Interactions: {stats['total_interactions']}\n"
                f"- Created: {stats['created_at']}\n"
                f"- Last Updated: {stats['last_updated']}\n"
                f"- Preferred Persona: {stats['preferred_persona'] or 'None'}"
            )
            
            await interaction.followup.send(response)
        except Exception as e:
            await interaction.followup.send(f"❌ Error getting persona stats: {str(e)}")

    @app_commands.command(name="persona", description="Select your preferred persona from available options")
    async def persona(self, interaction: discord.Interaction):
        """Select your preferred persona from available options."""
        await interaction.response.defer(ephemeral=True)

        try:
            # Get server settings
            settings = self.bot.settings_manager.get_server_settings(interaction.guild_id)
            personas = list(settings.get("personas", {}).keys())
            
            # Add "adaptive" as an option
            if "adaptive" not in personas:
                personas.append("adaptive")
            
            if not personas:
                await interaction.followup.send("❌ No personas are available in this server.", ephemeral=True)
                return

            # Create and send the select menu
            view = PersonaView(personas, str(interaction.user.id), self.user_manager)
            await interaction.followup.send(
                "**Select Your Preferred Persona**\n"
                "Choose a persona from the dropdown menu below:\n\n"
                "• **adaptive**: Your personalized AI assistant that learns from your interactions\n"
                "• Other personas: Pre-defined personalities with specific traits and styles",
                view=view,
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Error selecting persona: {str(e)}", ephemeral=True)

    @app_commands.command(name="maxhistory", description="Set the maximum number of previous interactions to remember for your persona")
    async def maxhistory(self, interaction: discord.Interaction, count: int):
        """Set the maximum number of previous interactions to remember for your persona."""
        await interaction.response.defer(ephemeral=True)  # Make response private

        try:
            # Validate the count
            if count < 1 or count > 30:
                await interaction.followup.send(
                    "❌ Please specify a number between 1 and 30 for max history.",
                    ephemeral=True
                )
                return

            # Update the user's max history setting
            user_id = str(interaction.user.id)
            self.user_manager.update_user_history_setting(user_id, "max_history", count)
            
            # Get current stats to show the change
            stats = self.user_manager.get_user_interaction_stats(user_id)
            
            response = (
                "✅ Max history updated successfully!\n\n"
                f"**Your Persona Settings:**\n"
                f"- Max History: {count} interactions\n"
                f"- Total Interactions: {stats['total_interactions']}\n"
                f"- Created: {stats['created_at']}\n"
                f"- Last Updated: {stats['last_updated']}\n\n"
                f"Your AI assistant will now remember your {count} most recent interactions when responding."
            )
            
            await interaction.followup.send(response, ephemeral=True)

        except Exception as e:
            print(f"Error updating max history: {e}")
            await interaction.followup.send(
                "❌ Error updating max history. Please try again.",
                ephemeral=True
            )

    @app_commands.command(name="recommend_personas", description="Get personalized persona recommendations")
    async def recommend_personas(self, interaction: discord.Interaction):
        """Get personalized persona recommendations based on your interactions."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get user's interaction history
            user_id = str(interaction.user.id)
            history = await self.bot.conversation_manager.get_conversation_history(user_id)
            
            # Get current personas
            current_personas = await self.user_manager.get_available_personas(user_id)
            
            # Generate recommendations
            recommendations = await self.persona_recommender.generate_recommendations(
                user_id, history, current_personas
            )
            
            # Format response
            response = "**🤖 Personalized Persona Recommendations**\n\n"
            
            for i, persona in enumerate(recommendations, 1):
                response += f"**{i}. {persona['name']}**\n"
                response += f"Role: {persona['role']}\n"
                response += f"Traits: {', '.join(persona['traits'])}\n"
                response += f"Style: {persona['style']}\n"
                response += f"Example: {persona['example']}\n\n"
            
            response += "To apply a recommended persona, use `/apply_persona <n>`"
            
            await interaction.followup.send(response, ephemeral=True)
            
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="recommend_personas",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                f"❌ Error generating recommendations: {str(e)} (Error ID: {error_id})",
                ephemeral=True
            )

    @app_commands.command(name="apply_persona", description="Apply a recommended persona")
    async def apply_persona(self, interaction: discord.Interaction, persona_name: str):
        """Apply a recommended persona to your available personas."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            user_id = str(interaction.user.id)
            
            # Apply the recommended persona
            persona = await self.persona_recommender.apply_recommendation(
                user_id, persona_name
            )
            
            if not persona:
                await interaction.followup.send(
                    f"❌ Persona '{persona_name}' not found in recommendations.",
                    ephemeral=True
                )
                return
            
            # Add the persona to user's available personas
            await self.user_manager.add_persona(user_id, persona)
            
            # Format response
            response = (
                f"✅ Successfully applied persona: **{persona['name']}**\n\n"
                f"Role: {persona['role']}\n"
                f"Traits: {', '.join(persona['traits'])}\n"
                f"Style: {persona['style']}\n\n"
                "You can now use `/persona` to switch to this persona."
            )
            
            await interaction.followup.send(response, ephemeral=True)
            
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="apply_persona",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                f"❌ Error applying persona: {str(e)} (Error ID: {error_id})",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(User(bot)) 