"""
Enhanced UI Components Module

This module provides rich, interactive UI elements for the bot,
including embeds, buttons, menus, and progress indicators.
"""

import discord
from typing import List, Dict, Optional, Union
from datetime import datetime
import logging

class UIComponents:
    """Handles creation of rich UI components for the bot."""
    
    def __init__(self):
        """Initialize UI components with default settings."""
        self.logger = logging.getLogger(__name__)
        
    def create_embed(
        self,
        title: str,
        description: str = None,
        color: Union[discord.Color, int] = discord.Color.blue(),
        fields: List[Dict] = None,
        thumbnail: str = None,
        image: str = None,
        footer_text: str = None,
        timestamp: bool = True
    ) -> discord.Embed:
        """Create a rich embed with customizable elements."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow() if timestamp else None
        )
        
        if fields:
            for field in fields:
                embed.add_field(
                    name=field.get("name", ""),
                    value=field.get("value", ""),
                    inline=field.get("inline", False)
                )
        
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        
        if image:
            embed.set_image(url=image)
        
        if footer_text:
            embed.set_footer(text=footer_text)
        
        return embed
    
    def create_paginated_embed(
        self,
        title: str,
        items: List[str],
        items_per_page: int = 10,
        color: Union[discord.Color, int] = discord.Color.blue(),
        description: str = None
    ) -> List[discord.Embed]:
        """Create a list of paginated embeds for displaying large sets of items."""
        embeds = []
        total_pages = (len(items) + items_per_page - 1) // items_per_page
        
        for page in range(total_pages):
            start_idx = page * items_per_page
            end_idx = min(start_idx + items_per_page, len(items))
            page_items = items[start_idx:end_idx]
            
            embed = self.create_embed(
                title=f"{title} (Page {page + 1}/{total_pages})",
                description=description,
                color=color,
                fields=[{
                    "name": "Items",
                    "value": "\n".join(page_items),
                    "inline": False
                }]
            )
            embeds.append(embed)
        
        return embeds
    
    def create_button(
        self,
        label: str,
        style: discord.ButtonStyle = discord.ButtonStyle.primary,
        custom_id: str = None,
        emoji: str = None,
        disabled: bool = False
    ) -> discord.ui.Button:
        """Create an interactive button with customizable properties."""
        return discord.ui.Button(
            label=label,
            style=style,
            custom_id=custom_id,
            emoji=emoji,
            disabled=disabled
        )
    
    def create_select_menu(
        self,
        placeholder: str,
        options: List[Dict],
        min_values: int = 1,
        max_values: int = 1,
        custom_id: str = None,
        disabled: bool = False
    ) -> discord.ui.Select:
        """Create a select menu with customizable options."""
        return discord.ui.Select(
            placeholder=placeholder,
            min_values=min_values,
            max_values=max_values,
            custom_id=custom_id,
            disabled=disabled,
            options=[
                discord.SelectOption(
                    label=option.get("label", ""),
                    value=option.get("value", ""),
                    description=option.get("description", ""),
                    emoji=option.get("emoji", None),
                    default=option.get("default", False)
                )
                for option in options
            ]
        )
    
    def create_progress_bar(
        self,
        current: int,
        total: int,
        width: int = 20,
        filled_char: str = "█",
        empty_char: str = "░"
    ) -> str:
        """Create a text-based progress bar."""
        if total <= 0:
            return ""
        
        filled_length = int(width * current / total)
        empty_length = width - filled_length
        
        return f"{filled_char * filled_length}{empty_char * empty_length}"
    
    def create_status_embed(
        self,
        title: str,
        status: str,
        details: Dict = None,
        color: Union[discord.Color, int] = discord.Color.blue()
    ) -> discord.Embed:
        """Create an embed for displaying status information."""
        fields = []
        if details:
            for key, value in details.items():
                fields.append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })
        
        return self.create_embed(
            title=title,
            description=status,
            color=color,
            fields=fields,
            timestamp=True
        )
    
    def create_error_embed(
        self,
        error: Exception,
        error_id: str = None,
        context: Dict = None
    ) -> discord.Embed:
        """Create an embed for displaying error information."""
        fields = []
        if error_id:
            fields.append({
                "name": "Error ID",
                "value": error_id,
                "inline": True
            })
        
        if context:
            for key, value in context.items():
                fields.append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })
        
        return self.create_embed(
            title="Error Occurred",
            description=str(error),
            color=discord.Color.red(),
            fields=fields,
            timestamp=True
        )
    
    def create_success_embed(
        self,
        title: str,
        message: str,
        details: Dict = None
    ) -> discord.Embed:
        """Create an embed for displaying success information."""
        fields = []
        if details:
            for key, value in details.items():
                fields.append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })
        
        return self.create_embed(
            title=title,
            description=message,
            color=discord.Color.green(),
            fields=fields,
            timestamp=True
        ) 