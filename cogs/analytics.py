import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from utils.error_handler import ErrorHandler
from utils.analytics_manager import AnalyticsManager
from utils.user_analytics import UserAnalytics
from utils.ui_components import UIComponents
from datetime import datetime

class Analytics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.error_handler = bot.error_handler
        self.analytics_manager = bot.analytics_manager
        self.user_analytics = bot.user_analytics
        self.ui_components = bot.ui_components

    @app_commands.command(name="analytics", description="View bot analytics (Admin only)")
    async def analytics(self, interaction: discord.Interaction, days: int = 30):
        """View bot analytics."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user has admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send(
                    "❌ You need administrator permissions to view analytics.",
                    ephemeral=True
                )
                return
            
            # Get usage statistics
            stats = self.analytics_manager.get_usage_stats(days)
            
            # Generate graphs
            usage_graph = self.analytics_manager.generate_usage_graph(days)
            command_graph = self.analytics_manager.generate_command_usage_graph(days)
            
            # Create embed with statistics
            embed = self.ui_components.create_embed(
                title="📊 Bot Analytics",
                description=f"Analytics for the last {days} days:",
                color=discord.Color.blue(),
                fields=[
                    {
                        "name": "Overview",
                        "value": f"""
Total Events: {stats['total_events']}
Unique Users: {stats['unique_users']}
Unique Guilds: {stats['unique_guilds']}
                        """,
                        "inline": False
                    },
                    {
                        "name": "Events by Type",
                        "value": "\n".join(f"- {type_}: {count}" for type_, count in stats['events_by_type'].items()),
                        "inline": False
                    }
                ],
                footer_text=f"Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            
            # Send embed with graphs
            await interaction.followup.send(embed=embed)
            
            if usage_graph:
                await interaction.channel.send(
                    "**Usage Over Time**",
                    file=discord.File(usage_graph, filename="usage.png")
                )
            
            if command_graph:
                await interaction.channel.send(
                    "**Command Usage Distribution**",
                    file=discord.File(command_graph, filename="commands.png")
                )
            
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="analytics",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                embed=self.ui_components.create_error_embed(
                    error=e,
                    error_id=error_id,
                    context={"command": "analytics"}
                ),
                ephemeral=True
            )

    @app_commands.command(name="user_analytics", description="View your personal analytics")
    async def user_analytics(self, interaction: discord.Interaction, days: int = 30):
        """View personal analytics."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get user analytics
            analytics = self.analytics_manager.get_user_analytics(str(interaction.user.id), days)
            
            if "error" in analytics:
                await interaction.followup.send(
                    embed=self.ui_components.create_status_embed(
                        title="No Data",
                        status="No analytics data found for your account.",
                        color=discord.Color.yellow()
                    ),
                    ephemeral=True
                )
                return
            
            # Generate activity graph
            activity_graph = self.analytics_manager.generate_user_activity_graph(str(interaction.user.id), days)
            
            # Create embed with statistics
            embed = self.ui_components.create_embed(
                title="👤 Your Analytics",
                description=f"Your activity for the last {days} days:",
                color=discord.Color.blue(),
                fields=[
                    {
                        "name": "Overview",
                        "value": f"""
Total Events: {analytics['total_events']}
Unique Guilds: {analytics['unique_guilds']}
                        """,
                        "inline": False
                    },
                    {
                        "name": "Most Used Commands",
                        "value": "\n".join(f"- {cmd}: {count}" for cmd, count in analytics['most_used_commands'].items()),
                        "inline": False
                    }
                ],
                footer_text=f"Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            
            # Send embed with graph
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            if activity_graph:
                await interaction.channel.send(
                    "**Your Activity Over Time**",
                    file=discord.File(activity_graph, filename="activity.png"),
                    ephemeral=True
                )
            
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="user_analytics",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                embed=self.ui_components.create_error_embed(
                    error=e,
                    error_id=error_id,
                    context={"command": "user_analytics"}
                ),
                ephemeral=True
            )

    @app_commands.command(name="guild_analytics", description="View guild analytics (Admin only)")
    async def guild_analytics(self, interaction: discord.Interaction, days: int = 30):
        """View guild analytics."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user has admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send(
                    "❌ You need administrator permissions to view guild analytics.",
                    ephemeral=True
                )
                return
            
            # Get guild analytics
            analytics = self.analytics_manager.get_guild_analytics(str(interaction.guild_id), days)
            
            if "error" in analytics:
                await interaction.followup.send(
                    embed=self.ui_components.create_status_embed(
                        title="No Data",
                        status="No analytics data found for this guild.",
                        color=discord.Color.yellow()
                    ),
                    ephemeral=True
                )
                return
            
            # Create embed with statistics
            embed = self.ui_components.create_embed(
                title="🏰 Guild Analytics",
                description=f"Analytics for {interaction.guild.name} ({days} days):",
                color=discord.Color.blue(),
                fields=[
                    {
                        "name": "Overview",
                        "value": f"""
Total Events: {analytics['total_events']}
Unique Users: {analytics['unique_users']}
                        """,
                        "inline": False
                    },
                    {
                        "name": "Most Active Users",
                        "value": "\n".join(f"- <@{user_id}>: {count} events" for user_id, count in analytics['most_active_users'].items()),
                        "inline": False
                    },
                    {
                        "name": "Most Used Commands",
                        "value": "\n".join(f"- {cmd}: {count}" for cmd, count in analytics['most_used_commands'].items()),
                        "inline": False
                    }
                ],
                footer_text=f"Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="guild_analytics",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                embed=self.ui_components.create_error_embed(
                    error=e,
                    error_id=error_id,
                    context={"command": "guild_analytics"}
                ),
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Analytics(bot)) 