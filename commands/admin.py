import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from utils.permissions import admin_only, check_admin_permissions
from utils.embeds import create_success_embed, create_error_embed
from database import reset_all_data

logger = logging.getLogger(__name__)

class AdminCommands(commands.Cog):
    """Administrative commands for bot management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="reset_all", description="Reset all data in the database (DANGEROUS)")
    async def reset_all(self, interaction: discord.Interaction):
        """Reset all data in the database"""
        if not await check_admin_permissions(interaction):
            return
            
        # Create confirmation view
        view = ResetConfirmationView()
        
        embed = discord.Embed(
            title="⚠️ DANGER ZONE",
            description="This will **permanently delete ALL data** including:\n\n"
                       "• All clubs and their finances\n"
                       "• All players and their values\n"
                       "• All transfer history\n"
                       "• All scheduled matches\n\n"
                       "**This action cannot be undone!**",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="info_bot", description="Show bot information and statistics")
    async def info_bot(self, interaction: discord.Interaction):
        """Show bot information"""
        if not await check_admin_permissions(interaction):
            return
            
        try:
            from database import get_all_clubs, get_db_connection
            
            # Get database stats
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) as count FROM clubs')
            club_count = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM players')
            player_count = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM transfers')
            transfer_count = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM matches')
            match_count = cursor.fetchone()['count']
            
            embed = discord.Embed(
                title="🤖 Football Club Management Bot",
                description="Comprehensive football club management system",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📊 Database Statistics",
                value=f"🏟️ Clubs: {club_count}\n"
                      f"⚽ Players: {player_count}\n"
                      f"🔄 Transfers: {transfer_count}\n"
                      f"📅 Matches: {match_count}",
                inline=True
            )
            
            embed.add_field(
                name="🌐 Bot Status",
                value=f"🟢 Online\n"
                      f"📡 Guilds: {len(self.bot.guilds)}\n"
                      f"👥 Users: {len(self.bot.users)}\n"
                      f"🔧 Commands: {len(self.bot.tree.get_commands())}",
                inline=True
            )
            
            embed.add_field(
                name="💻 System",
                value=f"🐍 Python {discord.__version__}\n"
                      f"📚 discord.py {discord.__version__}\n"
                      f"💾 SQLite Database\n"
                      f"🚀 Rate Limited",
                inline=True
            )
            
            embed.set_footer(text="Use /help to see all available commands")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in info_bot: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving bot information: {str(e)}"),
                ephemeral=True
            )

class ResetConfirmationView(discord.ui.View):
    """Confirmation view for reset operation"""
    
    def __init__(self):
        super().__init__(timeout=30)
    
    @discord.ui.button(label="CONFIRM RESET", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm the reset operation"""
        try:
            success = reset_all_data()
            
            if success:
                embed = create_success_embed("All data has been reset successfully!")
            else:
                embed = create_error_embed("Failed to reset data. Check logs for details.")
                
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Error in reset confirmation: {e}")
            await interaction.response.edit_message(
                embed=create_error_embed(f"Error during reset: {str(e)}"),
                view=None
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the reset operation"""
        embed = discord.Embed(
            title="✅ Reset Cancelled",
            description="No data was modified.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True
