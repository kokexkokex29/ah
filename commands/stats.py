import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from utils.embeds import create_stats_embed, create_error_embed
from utils.permissions import check_admin_permissions
from database import (
    get_top_players_by_value, get_richest_clubs, get_recent_transfers,
    get_all_clubs, get_db_connection
)

logger = logging.getLogger(__name__)

class StatsCommands(commands.Cog):
    """Commands for statistics and analytics"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="league_stats", description="Show overall league statistics")
    async def league_stats(self, interaction: discord.Interaction):
        """Show comprehensive league statistics"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get basic counts
            cursor.execute('SELECT COUNT(*) as count FROM clubs')
            club_count = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM players')
            player_count = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM transfers')
            transfer_count = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM matches WHERE match_time >= datetime("now")')
            upcoming_matches = cursor.fetchone()['count']
            
            # Get financial stats
            cursor.execute('SELECT SUM(money) as total, AVG(money) as avg FROM clubs')
            money_stats = cursor.fetchone()
            total_money = money_stats['total'] or 0
            avg_money = money_stats['avg'] or 0
            
            cursor.execute('SELECT SUM(value) as total, AVG(value) as avg FROM players')
            value_stats = cursor.fetchone()
            total_value = value_stats['total'] or 0
            avg_value = value_stats['avg'] or 0
            
            # Get free agents
            cursor.execute('SELECT COUNT(*) as count FROM players WHERE club_id IS NULL')
            free_agents = cursor.fetchone()['count']
            
            embed = discord.Embed(
                title="📊 League Statistics",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="🏟️ Clubs",
                value=f"**{club_count}** total clubs\n"
                      f"💰 Total money: €{total_money:,.2f}\n"
                      f"📊 Average money: €{avg_money:,.2f}",
                inline=True
            )
            
            embed.add_field(
                name="⚽ Players",
                value=f"**{player_count}** total players\n"
                      f"💎 Total value: €{total_value:,.2f}\n"
                      f"📊 Average value: €{avg_value:,.2f}\n"
                      f"🆓 Free agents: {free_agents}",
                inline=True
            )
            
            embed.add_field(
                name="📈 Activity",
                value=f"🔄 Total transfers: {transfer_count}\n"
                      f"📅 Upcoming matches: {upcoming_matches}",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting league stats: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving league statistics: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="club_rankings", description="Show club rankings by different criteria")
    @app_commands.describe(
        criteria="Ranking criteria",
        limit="Number of clubs to show (default: 10)"
    )
    @app_commands.choices(criteria=[
        app_commands.Choice(name="Money", value="money"),
        app_commands.Choice(name="Squad Value", value="squad_value"),
        app_commands.Choice(name="Player Count", value="player_count")
    ])
    async def club_rankings(
        self,
        interaction: discord.Interaction,
        criteria: str,
        limit: Optional[int] = 10
    ):
        """Show club rankings"""
        try:
            if limit is None or limit < 1 or limit > 25:
                limit = 10
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if criteria == "money":
                cursor.execute('SELECT * FROM clubs ORDER BY money DESC LIMIT ?', (limit,))
                clubs = [dict(row) for row in cursor.fetchall()]
                title = "💰 Richest Clubs"
                
                embed = create_stats_embed(title, clubs, "money", "name")
                
            elif criteria == "squad_value":
                cursor.execute('''
                    SELECT c.*, COALESCE(SUM(p.value), 0) as squad_value
                    FROM clubs c
                    LEFT JOIN players p ON c.id = p.club_id
                    GROUP BY c.id
                    ORDER BY squad_value DESC
                    LIMIT ?
                ''', (limit,))
                clubs = [dict(row) for row in cursor.fetchall()]
                title = "💎 Clubs by Squad Value"
                
                embed = create_stats_embed(title, clubs, "squad_value", "name")
                
            elif criteria == "player_count":
                cursor.execute('''
                    SELECT c.*, COUNT(p.id) as player_count
                    FROM clubs c
                    LEFT JOIN players p ON c.id = p.club_id
                    GROUP BY c.id
                    ORDER BY player_count DESC
                    LIMIT ?
                ''', (limit,))
                clubs = [dict(row) for row in cursor.fetchall()]
                title = "👥 Clubs by Player Count"
                
                embed = create_stats_embed(title, clubs, "player_count", "name")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting club rankings: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving club rankings: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="transfer_market", description="Show transfer market analysis")
    @app_commands.describe(limit="Number of transfers to analyze (default: 20)")
    async def transfer_market(self, interaction: discord.Interaction, limit: Optional[int] = 20):
        """Show transfer market statistics"""
        try:
            if limit is None or limit < 1 or limit > 50:
                limit = 20
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get transfer statistics
            cursor.execute('SELECT COUNT(*) as count, SUM(transfer_fee) as total, AVG(transfer_fee) as avg FROM transfers')
            stats = cursor.fetchone()
            total_transfers = stats['count']
            total_fees = stats['total'] or 0
            avg_fee = stats['avg'] or 0
            
            # Get biggest transfers
            cursor.execute('''
                SELECT t.transfer_fee, p.name as player_name, 
                       c1.name as from_club, c2.name as to_club
                FROM transfers t
                LEFT JOIN players p ON t.player_id = p.id
                LEFT JOIN clubs c1 ON t.from_club_id = c1.id
                LEFT JOIN clubs c2 ON t.to_club_id = c2.id
                ORDER BY t.transfer_fee DESC
                LIMIT ?
            ''', (limit,))
            
            big_transfers = [dict(row) for row in cursor.fetchall()]
            
            embed = discord.Embed(
                title="💼 Transfer Market Analysis",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="📊 Overview",
                value=f"🔄 Total transfers: {total_transfers}\n"
                      f"💰 Total fees: €{total_fees:,.2f}\n"
                      f"📊 Average fee: €{avg_fee:,.2f}",
                inline=False
            )
            
            if big_transfers:
                description = ""
                for i, transfer in enumerate(big_transfers[:10], 1):
                    from_club = transfer['from_club'] or "Free Agent"
                    description += f"{i}. **{transfer['player_name']}** - €{transfer['transfer_fee']:,.2f}\n"
                    description += f"   {from_club} → {transfer['to_club']}\n\n"
                
                embed.add_field(
                    name="💎 Biggest Transfers",
                    value=description,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting transfer market stats: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving transfer market data: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="compare_clubs", description="Compare two clubs side by side")
    @app_commands.describe(
        club1="First club name",
        club2="Second club name"
    )
    async def compare_clubs(self, interaction: discord.Interaction, club1: str, club2: str):
        """Compare two clubs"""
        try:
            from database import get_club_by_name, get_players_by_club
            
            # Get both clubs
            club1_data = get_club_by_name(club1)
            club2_data = get_club_by_name(club2)
            
            if not club1_data:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Club '{club1}' not found!"),
                    ephemeral=True
                )
                return
            
            if not club2_data:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Club '{club2}' not found!"),
                    ephemeral=True
                )
                return
            
            # Get squad data
            club1_players = get_players_by_club(club1_data['id'])
            club2_players = get_players_by_club(club2_data['id'])
            
            club1_value = sum(p['value'] for p in club1_players)
            club2_value = sum(p['value'] for p in club2_players)
            
            embed = discord.Embed(
                title=f"⚖️ Club Comparison",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name=f"🏟️ {club1_data['name']}",
                value=f"💰 Money: €{club1_data['money']:,.2f}\n"
                      f"👥 Players: {len(club1_players)}\n"
                      f"💎 Squad Value: €{club1_value:,.2f}\n"
                      f"📊 Avg Player Value: €{club1_value/len(club1_players):,.2f}" if club1_players else "€0",
                inline=True
            )
            
            embed.add_field(
                name=f"🏟️ {club2_data['name']}",
                value=f"💰 Money: €{club2_data['money']:,.2f}\n"
                      f"👥 Players: {len(club2_players)}\n"
                      f"💎 Squad Value: €{club2_value:,.2f}\n"
                      f"📊 Avg Player Value: €{club2_value/len(club2_players):,.2f}" if club2_players else "€0",
                inline=True
            )
            
            # Add comparison summary
            total1 = club1_data['money'] + club1_value
            total2 = club2_data['money'] + club2_value
            
            if total1 > total2:
                winner = club1_data['name']
                difference = total1 - total2
            elif total2 > total1:
                winner = club2_data['name']
                difference = total2 - total1
            else:
                winner = "Tie"
                difference = 0
            
            summary = f"🏆 **Overall Leader:** {winner}"
            if difference > 0:
                summary += f" (€{difference:,.2f} ahead)"
            
            embed.add_field(
                name="📊 Summary",
                value=summary,
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error comparing clubs: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error comparing clubs: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="create_embed", description="Create a custom embed with image")
    @app_commands.describe(
        title="Embed title",
        description="Embed description",
        color="Embed color (hex, e.g., #FF0000)",
        image="Image attachment from Discord"
    )
    async def create_embed(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        color: Optional[str] = None,
        image: Optional[discord.Attachment] = None
    ):
        """Create a custom embed"""
        if not await check_admin_permissions(interaction):
            return
            
        try:
            # Parse color
            embed_color = discord.Color.blue()  # default
            if color:
                try:
                    if color.startswith('#'):
                        embed_color = discord.Color(int(color[1:], 16))
                    else:
                        embed_color = discord.Color(int(color, 16))
                except ValueError:
                    embed_color = discord.Color.blue()
            
            # Create embed
            embed = discord.Embed(
                title=title,
                description=description,
                color=embed_color
            )
            
            # Add image if provided
            if image:
                if image.content_type and image.content_type.startswith('image/'):
                    embed.set_image(url=image.url)
                else:
                    await interaction.response.send_message(
                        embed=create_error_embed("Please provide a valid image file!"),
                        ephemeral=True
                    )
                    return
            
            embed.set_footer(text=f"Created by {interaction.user.display_name}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error creating custom embed: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error creating embed: {str(e)}"),
                ephemeral=True
            )
