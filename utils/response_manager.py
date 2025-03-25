from typing import Optional, Dict, List, Any
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
import discord
from .ui_components import UIComponents

@dataclass
class CommandState:
    """Represents the state of a command being processed."""
    interaction: discord.Interaction
    start_time: datetime
    status: str
    progress: float = 0.0
    message_id: Optional[str] = None
    is_long_running: bool = False

class ResponseManager:
    def __init__(self):
        """Initialize the response manager."""
        self.logger = logging.getLogger(__name__)
        self.active_commands: Dict[str, CommandState] = {}
        self.ui = UIComponents()
        
        # Command categories for different processing approaches
        self.long_running_commands = {
            "askgpt", "summarize", "analyze_code", "wiki"
        }
        
        # Maximum concurrent commands per user
        self.max_concurrent = 3
    
    async def start_command(self, interaction: discord.Interaction) -> bool:
        """Start processing a command and show initial feedback.
        
        Args:
            interaction: The Discord interaction
            
        Returns:
            bool: True if command can start, False if queued/rejected
        """
        user_id = str(interaction.user.id)
        command = interaction.command.name if interaction.command else "unknown"
        
        # Check concurrent commands for user
        user_commands = [cmd for cmd in self.active_commands.values() 
                        if str(cmd.interaction.user.id) == user_id]
        
        if len(user_commands) >= self.max_concurrent:
            try:
                await interaction.response.send_message(
                    embed=self.ui.create_error_embed(
                        title="Command Queued",
                        error=f"You have too many active commands. Please wait for them to complete.",
                        context={"command": command}
                    ),
                    ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    embed=self.ui.create_error_embed(
                        title="Command Queued",
                        error=f"You have too many active commands. Please wait for them to complete.",
                        context={"command": command}
                    ),
                    ephemeral=True
                )
            return False
        
        # Start command processing
        command_id = f"{user_id}_{datetime.now().timestamp()}"
        is_long_running = command in self.long_running_commands
        
        self.active_commands[command_id] = CommandState(
            interaction=interaction,
            start_time=datetime.now(),
            status="Starting...",
            is_long_running=is_long_running
        )
        
        # Show typing indicator for long-running commands
        if is_long_running:
            await interaction.response.defer()
        
        return True
    
    async def update_progress(self, interaction: discord.Interaction, progress: float, status: str = None):
        """Update the progress of a command.
        
        Args:
            interaction: The Discord interaction
            progress: Progress value between 0 and 1
            status: Optional status message
        """
        command_state = self._get_command_state(interaction)
        if not command_state:
            return
        
        command_state.progress = min(max(progress, 0.0), 1.0)
        if status:
            command_state.status = status
        
        if command_state.is_long_running:
            try:
                # Create progress embed
                embed = self.ui.create_status_embed(
                    title=f"Processing {interaction.command.name}",
                    status=command_state.status,
                    fields=[{
                        "name": "Progress",
                        "value": self.ui.create_progress_bar(
                            current=int(command_state.progress * 100),
                            total=100,
                            width=20
                        )
                    }]
                )
                
                if command_state.message_id:
                    # Update existing message
                    await interaction.edit_original_response(embed=embed)
                else:
                    # Send new progress message
                    response = await interaction.followup.send(embed=embed, ephemeral=True)
                    command_state.message_id = response.id
                    
            except Exception as e:
                self.logger.error(f"Error updating progress: {e}")
    
    async def end_command(self, interaction: discord.Interaction):
        """End command processing and cleanup.
        
        Args:
            interaction: The Discord interaction
        """
        command_state = self._get_command_state(interaction)
        if not command_state:
            return
        
        # Remove command from active commands
        user_id = str(interaction.user.id)
        command_id = next((cid for cid, cmd in self.active_commands.items() 
                          if str(cmd.interaction.user.id) == user_id), None)
        if command_id:
            del self.active_commands[command_id]
    
    def _get_command_state(self, interaction: discord.Interaction) -> Optional[CommandState]:
        """Get the state for a command.
        
        Args:
            interaction: The Discord interaction
            
        Returns:
            Optional[CommandState]: The command state if found
        """
        user_id = str(interaction.user.id)
        return next((cmd for cmd in self.active_commands.values() 
                    if str(cmd.interaction.user.id) == user_id), None)
    
    async def handle_error(self, interaction: discord.Interaction, error: Exception, error_id: str):
        """Handle command errors with improved feedback.
        
        Args:
            interaction: The Discord interaction
            error: The error that occurred
            error_id: The error ID for tracking
        """
        command_state = self._get_command_state(interaction)
        
        try:
            # Create error embed
            embed = self.ui.create_error_embed(
                error=error,
                error_id=error_id,
                context={"command": interaction.command.name if interaction.command else "unknown"}
            )
            
            if command_state and command_state.is_long_running:
                if command_state.message_id:
                    # Update progress message with error
                    await interaction.edit_original_response(embed=embed)
                else:
                    # Send new error message
                    await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                # Send error message
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    
        except Exception as e:
            self.logger.error(f"Error handling command error: {e}")
        
        # End command processing
        await self.end_command(interaction) 