import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from utils.permissions import admin_only, check_admin_permissions
from utils.embeds import (
    create_player_embed, create_success_embed, create_error_embed,
    create_transfer_embed, create_stats_embed
)
from database import (
    create_player, get_player_by_name, get_players_by_club, get_free_agents,
    update_player_value, transfer_player, get_club_by_name, get_top_players_by_value,
    get_recent_transfers
)

logger = logging.getLogger(__name__)

class PlayerCommands(commands.Cog):
    """Commands for player management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="create_player", description="Create a new player")
    @app_commands.describe(
        name="Player name",
        value="Player value in euros",
        position="Player position (optional)",
        age="Player age (optional)",
        club="Club name (optional, leave empty for free agent)"
    )
    async def create_player(
        self,
        interaction: discord.Interaction,
        name: str,
        value: float,
        position: Optional[str] = None,
        age: Optional[int] = None,
        club: Optional[str] = None
    ):
        """Create a new player"""
        if not await check_admin_permissions(interaction):
            return
            
        try:
            # Check if player already exists
            existing_player = get_player_by_name(name)
            if existing_player:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Player '{name}' already exists!"),
                    ephemeral=True
                )
                return
            
            # Validate inputs
            if value < 0:
                await interaction.response.send_message(
                    embed=create_error_embed("Player value cannot be negative!"),
                    ephemeral=True
                )
                return
            
            if age is not None and (age < 16 or age > 50):
                await interaction.response.send_message(
                    embed=create_error_embed("Player age must be between 16 and 50!"),
                    ephemeral=True
                )
                return
            
            # Get club ID if specified
            club_id = None
            club_name = None
            if club:
                club_data = get_club_by_name(club)
                if not club_data:
                    await interaction.response.send_message(
                        embed=create_error_embed(f"Club '{club}' not found!"),
                        ephemeral=True
                    )
                    return
                club_id = club_data['id']
                club_name = club_data['name']
            
            # Create player
            success = create_player(name, value, position or None, age, club_id)
            
            if success:
                player = get_player_by_name(name)
                embed = create_player_embed(player, club_name)
                embed.title = f"⚽ Player Created: {name}"
                embed.color = discord.Color.green()
                
                await interaction.response.send_message(embed=embed)
                logger.info(f"Player '{name}' created by {interaction.user}")
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Failed to create player. Please try again."),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error creating player: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error creating player: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="player_info", description="Show information about a player")
    @app_commands.describe(name="Player name")
    async def player_info(self, interaction: discord.Interaction, name: str):
        """Show player information"""
        try:
            player = get_player_by_name(name)
            if not player:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Player '{name}' not found!"),
                    ephemeral=True
                )
                return
            
            # Get club name if player has a club
            club_name = None
            if player['club_id']:
                from database import get_db_connection
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM clubs WHERE id = ?', (player['club_id'],))
                row = cursor.fetchone()
                if row:
                    club_name = row['name']
            
            embed = create_player_embed(player, club_name)
            
            # Add transfer history if available
            from database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT COUNT(*) as transfer_count 
                   FROM transfers WHERE player_id = ?''',
                (player['id'],)
            )
            transfer_count = cursor.fetchone()['transfer_count']
            
            if transfer_count > 0:
                embed.add_field(
                    name="📈 Career",
                    value=f"{transfer_count} transfers",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting player info: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving player information: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="set_player_value", description="Set a player's market value")
    @app_commands.describe(
        name="Player name",
        value="New value in euros"
    )
    async def set_player_value(
        self,
        interaction: discord.Interaction,
        name: str,
        value: float
    ):
        """Set player value"""
        if not await check_admin_permissions(interaction):
            return
            
        try:
            player = get_player_by_name(name)
            if not player:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Player '{name}' not found!"),
                    ephemeral=True
                )
                return
            
            if value < 0:
                await interaction.response.send_message(
                    embed=create_error_embed("Player value cannot be negative!"),
                    ephemeral=True
                )
                return
            
            old_value = player['value']
            success = update_player_value(player['id'], value)
            
            if success:
                embed = create_success_embed(
                    f"💎 {name}'s value updated from €{old_value:,.2f} to €{value:,.2f}"
                )
                await interaction.response.send_message(embed=embed)
                logger.info(f"Player '{name}' value updated to €{value:,.2f} by {interaction.user}")
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Failed to update player value."),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error setting player value: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error setting player value: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="transfer_player", description="Transfer a player between clubs")
    @app_commands.describe(
        player_name="Name of the player to transfer",
        to_club="Destination club name",
        fee="Transfer fee in euros (default: 0)"
    )
    async def transfer_player_command(
        self,
        interaction: discord.Interaction,
        player_name: str,
        to_club: str,
        fee: Optional[float] = 0.0
    ):
        """Transfer a player"""
        if not await check_admin_permissions(interaction):
            return
            
        try:
            # Get player
            player = get_player_by_name(player_name)
            if not player:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Player '{player_name}' not found!"),
                    ephemeral=True
                )
                return
            
            # Get destination club
            to_club_data = get_club_by_name(to_club)
            if not to_club_data:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Club '{to_club}' not found!"),
                    ephemeral=True
                )
                return
            
            # Check if player is already in the club
            if player['club_id'] == to_club_data['id']:
                await interaction.response.send_message(
                    embed=create_error_embed(f"{player_name} is already in {to_club}!"),
                    ephemeral=True
                )
                return
            
            # Validate transfer fee
            if fee is None:
                fee = 0.0
            if fee < 0:
                await interaction.response.send_message(
                    embed=create_error_embed("Transfer fee cannot be negative!"),
                    ephemeral=True
                )
                return
            
            # Check if destination club can afford the transfer
            if to_club_data['money'] < fee:
                await interaction.response.send_message(
                    embed=create_error_embed(
                        f"{to_club} cannot afford this transfer! "
                        f"(Available: €{to_club_data['money']:,.2f}, Required: €{fee:,.2f})"
                    ),
                    ephemeral=True
                )
                return
            
            # Get source club name
            from_club_name = None
            if player['club_id']:
                from database import get_db_connection
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM clubs WHERE id = ?', (player['club_id'],))
                row = cursor.fetchone()
                if row:
                    from_club_name = row['name']
            
            # Perform transfer
            success = transfer_player(player['id'], to_club_data['id'], fee)
            
            if success:
                # Create transfer embed
                transfer_data = {
                    'player_name': player_name,
                    'from_club_name': from_club_name or "Free Agent",
                    'to_club_name': to_club,
                    'transfer_fee': fee
                }
                
                embed = create_transfer_embed(transfer_data)
                await interaction.response.send_message(embed=embed)
                
                logger.info(f"Player '{player_name}' transferred to '{to_club}' for €{fee:,.2f} by {interaction.user}")
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Failed to complete transfer. Please try again."),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error transferring player: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error transferring player: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="free_agents", description="Show players without a club")
    async def free_agents(self, interaction: discord.Interaction):
        """Show free agents"""
        try:
            players = get_free_agents()
            
            if not players:
                await interaction.response.send_message(
                    embed=create_error_embed("No free agents available!"),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="🆓 Free Agents",
                color=discord.Color.orange()
            )
            
            description = ""
            for player in players[:20]:  # Limit to 20 players
                description += f"⚽ **{player['name']}** - €{player['value']:,.2f}"
                if player['position']:
                    description += f" ({player['position']})"
                if player['age']:
                    description += f" - {player['age']} years"
                description += "\n"
            
            embed.description = description
            
            if len(players) > 20:
                embed.set_footer(text=f"Showing 20 of {len(players)} free agents")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting free agents: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving free agents: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="club_squad", description="Show all players in a club")
    @app_commands.describe(club_name="Name of the club")
    async def club_squad(self, interaction: discord.Interaction, club_name: str):
        """Show club squad"""
        try:
            club = get_club_by_name(club_name)
            if not club:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Club '{club_name}' not found!"),
                    ephemeral=True
                )
                return
            
            players = get_players_by_club(club['id'])
            
            if not players:
                await interaction.response.send_message(
                    embed=create_error_embed(f"{club_name} has no players!"),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"👥 {club_name} Squad",
                color=discord.Color.blue()
            )
            
            total_value = sum(player['value'] for player in players)
            embed.description = f"**{len(players)} players** • **Total value: €{total_value:,.2f}**\n\n"
            
            description = ""
            for player in players:
                description += f"⚽ **{player['name']}** - €{player['value']:,.2f}"
                if player['position']:
                    description += f" ({player['position']})"
                if player['age']:
                    description += f" - {player['age']} years"
                description += "\n"
            
            embed.description += description
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting club squad: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving club squad: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="top_players", description="Show the most valuable players")
    @app_commands.describe(limit="Number of players to show (default: 10)")
    async def top_players(self, interaction: discord.Interaction, limit: Optional[int] = 10):
        """Show top players by value"""
        try:
            if limit is None or limit < 1 or limit > 25:
                limit = 10
            
            players = get_top_players_by_value(limit)
            
            if not players:
                await interaction.response.send_message(
                    embed=create_error_embed("No players found!"),
                    ephemeral=True
                )
                return
            
            embed = create_stats_embed(
                "⭐ Most Valuable Players",
                players,
                "value",
                "name"
            )
            
            # Add club information
            description = ""
            for i, player in enumerate(players, 1):
                club_info = f" ({player['club_name']})" if player.get('club_name') else " (Free Agent)"
                description += f"{i}. **{player['name']}**{club_info} - €{player['value']:,.2f}\n"
            
            embed.description = description
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting top players: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving top players: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="recent_transfers", description="Show recent player transfers")
    @app_commands.describe(limit="Number of transfers to show (default: 10)")
    async def recent_transfers_command(self, interaction: discord.Interaction, limit: Optional[int] = 10):
        """Show recent transfers"""
        try:
            if limit is None or limit < 1 or limit > 25:
                limit = 10
            
            transfers = get_recent_transfers(limit)
            
            if not transfers:
                await interaction.response.send_message(
                    embed=create_error_embed("No transfers found!"),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="🔄 Recent Transfers",
                color=discord.Color.orange()
            )
            
            description = ""
            for i, transfer in enumerate(transfers, 1):
                from_club = transfer['from_club_name'] or "Free Agent"
                description += f"{i}. **{transfer['player_name']}**\n"
                description += f"   {from_club} → {transfer['to_club_name']}\n"
                description += f"   💰 €{transfer['transfer_fee']:,.2f}\n\n"
            
            embed.description = description
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting recent transfers: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving recent transfers: {str(e)}"),
                ephemeral=True
            )
