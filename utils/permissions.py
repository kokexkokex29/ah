import discord
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def is_administrator(user: discord.Member) -> bool:
    """Check if user has administrator permissions"""
    if hasattr(user, 'guild_permissions'):
        return user.guild_permissions.administrator
    return False

def admin_only():
    """Decorator to restrict commands to administrators only"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not is_administrator(interaction.user):
                await interaction.response.send_message(
                    "❌ This command is restricted to administrators only.",
                    ephemeral=True
                )
                return
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator

async def check_admin_permissions(interaction: discord.Interaction) -> bool:
    """Check if user has admin permissions and respond if not"""
    if not is_administrator(interaction.user):
        await interaction.response.send_message(
            "❌ This command is restricted to administrators only.",
            ephemeral=True
        )
        return False
    return True
