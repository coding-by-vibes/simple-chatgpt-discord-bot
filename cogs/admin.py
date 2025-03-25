import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from utils.error_handler import ErrorHandler
from utils.rbac_manager import RBACManager, Permission, Role
from utils.ui_components import UIComponents

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.error_handler = bot.error_handler
        self.rbac_manager = bot.rbac_manager
        self.ui_components = bot.ui_components

    @app_commands.command(name="errorlog", description="View error logs (Admin only)")
    async def errorlog(self, interaction: discord.Interaction, error_id: Optional[str] = None):
        """View error logs (Admin only)."""
        await interaction.response.defer(ephemeral=True)

        try:
            # Check if user has admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.followup.send("❌ You need administrator permissions to view error logs.", ephemeral=True)
                return

            if error_id:
                # Get specific error
                error = self.error_handler.get_error(error_id)
                if not error:
                    await interaction.followup.send(f"❌ No error log found with ID: {error_id}", ephemeral=True)
                    return

                # Format error details
                response = (
                    f"**Error Log: {error_id}**\n\n"
                    f"**Timestamp:** {error['timestamp']}\n"
                    f"**Type:** {error['error_type']}\n"
                    f"**Message:** {error['error_message']}\n"
                    f"**Command:** {error['command'] or 'N/A'}\n"
                    f"**User:** {error['user_id'] or 'N/A'}\n"
                    f"**Guild:** {error['guild_id'] or 'N/A'}\n\n"
                    "**Suggested Fixes:**\n"
                )

                # Add immediate fixes
                if error['suggested_fixes']['immediate_fixes']:
                    response += "\n**Immediate Fixes:**\n"
                    for fix in error['suggested_fixes']['immediate_fixes']:
                        response += f"- {fix}\n"

                # Add preventive measures
                if error['suggested_fixes']['preventive_measures']:
                    response += "\n**Preventive Measures:**\n"
                    for measure in error['suggested_fixes']['preventive_measures']:
                        response += f"- {measure}\n"

                # Add improvement suggestions
                if error['suggested_fixes']['improvement_suggestions']:
                    response += "\n**Improvement Suggestions:**\n"
                    for suggestion in error['suggested_fixes']['improvement_suggestions']:
                        response += f"- {suggestion}\n"

                # Add traceback if available
                if error['traceback']:
                    response += f"\n**Traceback:**\n```\n{error['traceback']}\n```"

            else:
                # Get all errors
                errors = self.error_handler.get_all_errors()
                if not errors:
                    await interaction.followup.send("No error logs found.", ephemeral=True)
                    return

                # Format error list
                response = "**Recent Error Logs:**\n\n"
                for error in errors[:10]:  # Show last 10 errors
                    response += (
                        f"**ID:** {error['error_id']}\n"
                        f"**Time:** {error['timestamp']}\n"
                        f"**Type:** {error['error_type']}\n"
                        f"**Command:** {error['command'] or 'N/A'}\n"
                        f"**User:** {error['user_id'] or 'N/A'}\n"
                        "---\n"
                    )

            # Send response
            if len(response) > 2000:
                # Split into chunks
                chunks = [response[i:i+1990] for i in range(0, len(response), 1990)]
                for chunk in chunks:
                    await interaction.followup.send(chunk, ephemeral=True)
            else:
                await interaction.followup.send(response, ephemeral=True)

        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="errorlog",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                f"❌ Error viewing logs: {str(e)} (Error ID: {error_id})",
                ephemeral=True
            )

    @app_commands.command(name="set_role", description="Set a user's role (Admin only)")
    async def set_role(self, interaction: discord.Interaction, user: discord.Member, role: str):
        """Set a user's role."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if command user has permission
            if not self.rbac_manager.has_permission(str(interaction.user.id), Permission.MANAGE_USERS):
                await interaction.followup.send(
                    "❌ You don't have permission to manage user roles.",
                    ephemeral=True
                )
                return
            
            # Validate role
            if role not in [r.value for r in Role]:
                await interaction.followup.send(
                    f"❌ Invalid role. Available roles: {', '.join(r.value for r in Role)}",
                    ephemeral=True
                )
                return
            
            # Set the role
            success = self.rbac_manager.set_user_role(str(user.id), role)
            if success:
                await interaction.followup.send(
                    f"✅ Successfully set {user.mention}'s role to {role}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Failed to set user role.",
                    ephemeral=True
                )
                
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="set_role",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                f"❌ Error setting role: {str(e)} (Error ID: {error_id})",
                ephemeral=True
            )

    @app_commands.command(name="view_role", description="View a user's role")
    async def view_role(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """View a user's role."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # If no user specified, show own role
            target_user = user or interaction.user
            
            # Check if user has permission to view other users' roles
            if user and not self.rbac_manager.has_permission(str(interaction.user.id), Permission.VIEW_USERS):
                await interaction.followup.send(
                    "❌ You don't have permission to view other users' roles.",
                    ephemeral=True
                )
                return
            
            # Get the role
            role = self.rbac_manager.get_user_role(str(target_user.id))
            
            await interaction.followup.send(
                f"{target_user.mention}'s role is: {role}",
                ephemeral=True
            )
                
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="view_role",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                f"❌ Error viewing role: {str(e)} (Error ID: {error_id})",
                ephemeral=True
            )

    @app_commands.command(name="list_permissions", description="List permissions for a role")
    async def list_permissions(self, interaction: discord.Interaction, role: str):
        """List permissions for a role."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user has permission
            if not self.rbac_manager.has_permission(str(interaction.user.id), Permission.VIEW_SETTINGS):
                await interaction.followup.send(
                    "❌ You don't have permission to view role permissions.",
                    ephemeral=True
                )
                return
            
            # Validate role
            if role not in [r.value for r in Role]:
                await interaction.followup.send(
                    f"❌ Invalid role. Available roles: {', '.join(r.value for r in Role)}",
                    ephemeral=True
                )
                return
            
            # Get permissions
            permissions = self.rbac_manager.get_role_permissions(role)
            
            # Format permissions list
            permissions_list = "\n".join([f"- {perm}" for perm in sorted(permissions)])
            
            await interaction.followup.send(
                f"**Permissions for role {role}:**\n{permissions_list}",
                ephemeral=True
            )
                
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="list_permissions",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                f"❌ Error listing permissions: {str(e)} (Error ID: {error_id})",
                ephemeral=True
            )

    @app_commands.command(name="add_permission", description="Add a permission to a role (Admin only)")
    async def add_permission(self, interaction: discord.Interaction, role: str, permission: str):
        """Add a permission to a role."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user has permission
            if not self.rbac_manager.has_permission(str(interaction.user.id), Permission.MANAGE_SETTINGS):
                await interaction.followup.send(
                    "❌ You don't have permission to manage role permissions.",
                    ephemeral=True
                )
                return
            
            # Validate role
            if role not in [r.value for r in Role]:
                await interaction.followup.send(
                    f"❌ Invalid role. Available roles: {', '.join(r.value for r in Role)}",
                    ephemeral=True
                )
                return
            
            # Validate permission
            try:
                perm = Permission(permission)
            except ValueError:
                await interaction.followup.send(
                    f"❌ Invalid permission. Available permissions: {', '.join(p.value for p in Permission)}",
                    ephemeral=True
                )
                return
            
            # Add permission
            success = self.rbac_manager.add_role_permission(role, perm)
            if success:
                await interaction.followup.send(
                    f"✅ Successfully added permission {permission} to role {role}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Failed to add permission to role.",
                    ephemeral=True
                )
                
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="add_permission",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                f"❌ Error adding permission: {str(e)} (Error ID: {error_id})",
                ephemeral=True
            )

    @app_commands.command(name="remove_permission", description="Remove a permission from a role (Admin only)")
    async def remove_permission(self, interaction: discord.Interaction, role: str, permission: str):
        """Remove a permission from a role."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user has permission
            if not self.rbac_manager.has_permission(str(interaction.user.id), Permission.MANAGE_SETTINGS):
                await interaction.followup.send(
                    "❌ You don't have permission to manage role permissions.",
                    ephemeral=True
                )
                return
            
            # Validate role
            if role not in [r.value for r in Role]:
                await interaction.followup.send(
                    f"❌ Invalid role. Available roles: {', '.join(r.value for r in Role)}",
                    ephemeral=True
                )
                return
            
            # Validate permission
            try:
                perm = Permission(permission)
            except ValueError:
                await interaction.followup.send(
                    f"❌ Invalid permission. Available permissions: {', '.join(p.value for p in Permission)}",
                    ephemeral=True
                )
                return
            
            # Remove permission
            success = self.rbac_manager.remove_role_permission(role, perm)
            if success:
                await interaction.followup.send(
                    f"✅ Successfully removed permission {permission} from role {role}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Failed to remove permission from role.",
                    ephemeral=True
                )
                
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="remove_permission",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                f"❌ Error removing permission: {str(e)} (Error ID: {error_id})",
                ephemeral=True
            )

    @app_commands.command(name="reset_permissions", description="Reset all role permissions to default (Admin only)")
    async def reset_permissions(self, interaction: discord.Interaction):
        """Reset all role permissions to their default values."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user has permission
            if not self.rbac_manager.has_permission(str(interaction.user.id), Permission.MANAGE_SETTINGS):
                await interaction.followup.send(
                    "❌ You don't have permission to manage role permissions.",
                    ephemeral=True
                )
                return
            
            # Reset permissions
            success = self.rbac_manager.reset_role_permissions()
            if success:
                await interaction.followup.send(
                    "✅ Successfully reset all role permissions to default values.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Failed to reset role permissions.",
                    ephemeral=True
                )
                
        except Exception as e:
            error_id = self.error_handler.log_error(
                e,
                command="reset_permissions",
                user_id=str(interaction.user.id),
                guild_id=str(interaction.guild_id)
            )
            await interaction.followup.send(
                f"❌ Error resetting permissions: {str(e)} (Error ID: {error_id})",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Admin(bot)) 