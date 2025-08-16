import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from utils.permissions import admin_only, check_admin_permissions
from utils.embeds import (
    create_club_embed, create_success_embed, create_error_embed,
    create_stats_embed
)
from database import (
    create_club, get_club_by_owner, get_club_by_name, get_all_clubs,
    update_club_money, update_club_role, delete_club, get_players_by_club, get_richest_clubs
)

logger = logging.getLogger(__name__)

class ClubCommands(commands.Cog):
    """Commands for club management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="create_club", description="Create a new football club")
    @app_commands.describe(
        name="Name of the club",
        owner="User who will own the club",
        initial_money="Starting money in euros (default: 0)",
        role="Role for club players (optional)"
    )
    async def create_club_command(
        self, 
        interaction: discord.Interaction, 
        name: str,
        owner: discord.Member,
        initial_money: Optional[float] = 0.0,
        role: Optional[discord.Role] = None
    ):
        """Create a new club"""
        if not await check_admin_permissions(interaction):
            return
            
        try:
            # Check if club name already exists
            existing_club = get_club_by_name(name)
            if existing_club:
                await interaction.response.send_message(
                    embed=create_error_embed(f"A club named '{name}' already exists!"),
                    ephemeral=True
                )
                return
            
            # Check if user already owns a club
            existing_owner_club = get_club_by_owner(owner.id)
            if existing_owner_club:
                await interaction.response.send_message(
                    embed=create_error_embed(f"{owner.mention} already owns '{existing_owner_club['name']}'!"),
                    ephemeral=True
                )
                return
            
            # Create the club
            role_id = role.id if role else None
            success = create_club(name, owner.id, initial_money or 0.0, role_id)
            
            if success:
                # Get the created club to show details
                club = get_club_by_name(name)
                embed = create_club_embed(club)
                embed.title = f"🏟️ Club Created: {name}"
                embed.color = discord.Color.green()
                
                await interaction.response.send_message(embed=embed)
                logger.info(f"Club '{name}' created by {interaction.user} for {owner}")
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Failed to create club. Please try again."),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error creating club: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error creating club: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="club_info", description="Show information about a club")
    @app_commands.describe(name="Name of the club")
    async def club_info(self, interaction: discord.Interaction, name: str):
        """Show club information"""
        try:
            club = get_club_by_name(name)
            if not club:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Club '{name}' not found!"),
                    ephemeral=True
                )
                return
            
            # Get club players
            players = get_players_by_club(club['id'])
            
            embed = create_club_embed(club)
            
            if players:
                total_value = sum(player['value'] for player in players)
                embed.add_field(
                    name="👥 Squad",
                    value=f"{len(players)} players\n€{total_value:,.2f} total value",
                    inline=True
                )
                
                # Show top 5 most valuable players
                top_players = sorted(players, key=lambda p: p['value'], reverse=True)[:5]
                if top_players:
                    player_list = "\n".join([
                        f"⚽ {player['name']} - €{player['value']:,.2f}"
                        for player in top_players
                    ])
                    embed.add_field(
                        name="🌟 Top Players",
                        value=player_list,
                        inline=False
                    )
            else:
                embed.add_field(
                    name="👥 Squad",
                    value="No players",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting club info: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving club information: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="list_clubs", description="List all clubs")
    async def list_clubs(self, interaction: discord.Interaction):
        """List all clubs"""
        try:
            clubs = get_all_clubs()
            
            if not clubs:
                await interaction.response.send_message(
                    embed=create_error_embed("No clubs found!"),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="🏟️ All Football Clubs",
                color=discord.Color.blue()
            )
            
            description = ""
            for club in clubs:
                owner = self.bot.get_user(club['owner_id'])
                owner_name = owner.display_name if owner else "Unknown User"
                description += f"**{club['name']}**\n"
                description += f"👤 Owner: {owner_name}\n"
                description += f"💰 Money: €{club['money']:,.2f}\n\n"
            
            embed.description = description
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing clubs: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error listing clubs: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="set_club_money", description="Set a club's money amount")
    @app_commands.describe(
        club_name="Name of the club",
        amount="New money amount in euros"
    )
    async def set_club_money(
        self, 
        interaction: discord.Interaction, 
        club_name: str,
        amount: float
    ):
        """Set club money"""
        if not await check_admin_permissions(interaction):
            return
            
        try:
            club = get_club_by_name(club_name)
            if not club:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Club '{club_name}' not found!"),
                    ephemeral=True
                )
                return
            
            if amount < 0:
                await interaction.response.send_message(
                    embed=create_error_embed("Money amount cannot be negative!"),
                    ephemeral=True
                )
                return
            
            success = update_club_money(club['id'], amount)
            
            if success:
                embed = create_success_embed(
                    f"💰 {club_name}'s money updated to €{amount:,.2f}"
                )
                await interaction.response.send_message(embed=embed)
                logger.info(f"Club '{club_name}' money set to €{amount:,.2f} by {interaction.user}")
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Failed to update club money."),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error setting club money: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error setting club money: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="set_club_role", description="Assign a Discord role to a club for notifications")
    @app_commands.describe(
        club_name="Name of the club",
        role="Discord role to assign to the club (leave empty to remove role)"
    )
    async def set_club_role(
        self, 
        interaction: discord.Interaction, 
        club_name: str,
        role: Optional[discord.Role] = None
    ):
        """Set club role for notifications"""
        if not await check_admin_permissions(interaction):
            return
            
        try:
            club = get_club_by_name(club_name)
            if not club:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Club '{club_name}' not found!"),
                    ephemeral=True
                )
                return
            
            role_id = role.id if role else None
            success = update_club_role(club['id'], role_id)
            
            if success:
                if role:
                    embed = create_success_embed(
                        f"🎭 {club_name} is now linked to role {role.mention}\n\nMatch notifications will be sent to all members of this role."
                    )
                else:
                    embed = create_success_embed(
                        f"🎭 Role removed from {club_name}\n\nMatch notifications will now be sent to the club owner only."
                    )
                await interaction.response.send_message(embed=embed)
                logger.info(f"Club '{club_name}' role updated by {interaction.user}")
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Failed to update club role."),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error setting club role: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error setting club role: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="delete_club", description="Delete a club and all related data")
    @app_commands.describe(name="Name of the club to delete")
    async def delete_club_command(self, interaction: discord.Interaction, name: str):
        """Delete a club"""
        if not await check_admin_permissions(interaction):
            return
            
        try:
            club = get_club_by_name(name)
            if not club:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Club '{name}' not found!"),
                    ephemeral=True
                )
                return
            
            # Create confirmation view
            view = DeleteClubConfirmationView(club['id'], name)
            
            embed = discord.Embed(
                title="⚠️ Delete Club",
                description=f"Are you sure you want to delete **{name}**?\n\n"
                           "This will also:\n"
                           "• Release all players to free agency\n"
                           "• Delete all transfer history\n"
                           "• Cancel all scheduled matches\n\n"
                           "**This action cannot be undone!**",
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in delete club: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error deleting club: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="richest_clubs", description="Show the richest clubs")
    @app_commands.describe(limit="Number of clubs to show (default: 10)")
    async def richest_clubs(self, interaction: discord.Interaction, limit: Optional[int] = 10):
        """Show richest clubs"""
        try:
            if limit is None or limit < 1 or limit > 25:
                limit = 10
            
            clubs = get_richest_clubs(limit)
            
            if not clubs:
                await interaction.response.send_message(
                    embed=create_error_embed("No clubs found!"),
                    ephemeral=True
                )
                return
            
            embed = create_stats_embed(
                "💰 Richest Clubs",
                clubs,
                "money",
                "name"
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting richest clubs: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving richest clubs: {str(e)}"),
                ephemeral=True
            )

class DeleteClubConfirmationView(discord.ui.View):
    """Confirmation view for club deletion"""
    
    def __init__(self, club_id: int, club_name: str):
        super().__init__(timeout=30)
        self.club_id = club_id
        self.club_name = club_name
    
    @discord.ui.button(label="DELETE CLUB", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirm club deletion"""
        try:
            success = delete_club(self.club_id)
            
            if success:
                embed = create_success_embed(f"Club '{self.club_name}' has been deleted!")
            else:
                embed = create_error_embed("Failed to delete club. Check logs for details.")
                
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Error in club deletion: {e}")
            await interaction.response.edit_message(
                embed=create_error_embed(f"Error during deletion: {str(e)}"),
                view=None
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel club deletion"""
        embed = discord.Embed(
            title="✅ Deletion Cancelled",
            description=f"Club '{self.club_name}' was not deleted.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def on_timeout(self):
        """Handle timeout"""
        for item in self.children:
            item.disabled = True
