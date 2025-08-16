import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
import logging
from datetime import datetime, timedelta
from utils.permissions import admin_only, check_admin_permissions
from utils.embeds import (
    create_match_embed, create_success_embed, create_error_embed
)
from database import create_match, get_club_by_name

logger = logging.getLogger(__name__)

class MatchCommands(commands.Cog):
    """Commands for match management"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="create_match", description="Schedule a match between two teams")
    @app_commands.describe(
        team1="First team (club name)",
        team2="Second team (club name)",
        year="Year (e.g., 2025)",
        month="Month (1-12)",
        day="Day (1-31)",
        hour="Hour (0-23)",
        minute="Minute (0-59)"
    )
    async def create_match(
        self,
        interaction: discord.Interaction,
        team1: str,
        team2: str,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int
    ):
        """Create a match between two teams"""
        if not await check_admin_permissions(interaction):
            return
            
        try:
            # Validate teams
            team1_data = get_club_by_name(team1)
            if not team1_data:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Team '{team1}' not found!"),
                    ephemeral=True
                )
                return
            
            team2_data = get_club_by_name(team2)
            if not team2_data:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Team '{team2}' not found!"),
                    ephemeral=True
                )
                return
            
            if team1_data['id'] == team2_data['id']:
                await interaction.response.send_message(
                    embed=create_error_embed("A team cannot play against itself!"),
                    ephemeral=True
                )
                return
            
            # Validate and create datetime
            try:
                match_time = datetime(year, month, day, hour, minute)
            except ValueError as e:
                await interaction.response.send_message(
                    embed=create_error_embed(f"Invalid date/time: {str(e)}"),
                    ephemeral=True
                )
                return
            
            # Check if match is in the future
            if match_time <= datetime.now():
                await interaction.response.send_message(
                    embed=create_error_embed("Match time must be in the future!"),
                    ephemeral=True
                )
                return
            
            # Create the match
            success = create_match(team1_data['id'], team2_data['id'], match_time)
            
            if success:
                # Create match embed
                match_data = {
                    'match_time': match_time,
                    'team1_id': team1_data['id'],
                    'team2_id': team2_data['id']
                }
                
                embed = create_match_embed(match_data, team1, team2)
                embed.title = "📅 Match Scheduled"
                embed.color = discord.Color.green()
                
                await interaction.response.send_message(embed=embed)
                
                # Send DMs to team role members
                try:
                    dm_embed = create_match_embed(match_data, team1, team2)
                    dm_embed.title = "📅 You have a scheduled match!"
                    dm_embed.color = discord.Color.blue()
                    
                    # Send to team1 role members
                    if team1_data.get('role_id'):
                        guild = interaction.guild
                        team1_role = guild.get_role(team1_data['role_id'])
                        if team1_role:
                            for member in team1_role.members:
                                try:
                                    await member.send(embed=dm_embed)
                                except discord.Forbidden:
                                    logger.warning(f"Could not send DM to {member}")
                    else:
                        # Fallback to owner if no role set
                        team1_owner = self.bot.get_user(team1_data['owner_id'])
                        if team1_owner:
                            try:
                                await team1_owner.send(embed=dm_embed)
                            except discord.Forbidden:
                                logger.warning(f"Could not send DM to {team1_owner}")
                    
                    # Send to team2 role members
                    if team2_data.get('role_id'):
                        guild = interaction.guild
                        team2_role = guild.get_role(team2_data['role_id'])
                        if team2_role:
                            for member in team2_role.members:
                                try:
                                    await member.send(embed=dm_embed)
                                except discord.Forbidden:
                                    logger.warning(f"Could not send DM to {member}")
                    else:
                        # Fallback to owner if no role set
                        team2_owner = self.bot.get_user(team2_data['owner_id'])
                        if team2_owner and team2_owner.id != team1_data['owner_id']:
                            try:
                                await team2_owner.send(embed=dm_embed)
                            except discord.Forbidden:
                                logger.warning(f"Could not send DM to {team2_owner}")
                            
                except Exception as e:
                    logger.error(f"Error sending match DMs: {e}")
                
                logger.info(f"Match created: {team1} vs {team2} at {match_time} by {interaction.user}")
            else:
                await interaction.response.send_message(
                    embed=create_error_embed("Failed to create match. Please try again."),
                    ephemeral=True
                )
                
        except Exception as e:
            logger.error(f"Error creating match: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error creating match: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="upcoming_matches", description="Show upcoming matches")
    @app_commands.describe(days="Number of days to look ahead (default: 7)")
    async def upcoming_matches(self, interaction: discord.Interaction, days: Optional[int] = 7):
        """Show upcoming matches"""
        try:
            if days is None or days < 1 or days > 30:
                days = 7
            
            from database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            end_time = datetime.now() + timedelta(days=days)
            
            cursor.execute(
                '''SELECT m.*, c1.name as team1_name, c2.name as team2_name
                   FROM matches m
                   LEFT JOIN clubs c1 ON m.team1_id = c1.id
                   LEFT JOIN clubs c2 ON m.team2_id = c2.id
                   WHERE m.match_time BETWEEN ? AND ?
                   ORDER BY m.match_time ASC''',
                (datetime.now(), end_time)
            )
            
            matches = [dict(row) for row in cursor.fetchall()]
            
            if not matches:
                await interaction.response.send_message(
                    embed=create_error_embed(f"No matches scheduled in the next {days} days!"),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"📅 Upcoming Matches ({days} days)",
                color=discord.Color.blue()
            )
            
            description = ""
            for i, match in enumerate(matches, 1):
                match_time = datetime.fromisoformat(match['match_time']) if isinstance(match['match_time'], str) else match['match_time']
                description += f"{i}. **{match['team1_name']} vs {match['team2_name']}**\n"
                description += f"   📅 <t:{int(match_time.timestamp())}:F>\n"
                description += f"   ⏰ <t:{int(match_time.timestamp())}:R>\n\n"
            
            embed.description = description
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting upcoming matches: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving upcoming matches: {str(e)}"),
                ephemeral=True
            )
    
    @app_commands.command(name="my_matches", description="Show matches for your club")
    async def my_matches(self, interaction: discord.Interaction):
        """Show matches for the user's club"""
        try:
            from database import get_club_by_owner
            
            # Get user's club
            club = get_club_by_owner(interaction.user.id)
            if not club:
                await interaction.response.send_message(
                    embed=create_error_embed("You don't own a club!"),
                    ephemeral=True
                )
                return
            
            from database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute(
                '''SELECT m.*, c1.name as team1_name, c2.name as team2_name
                   FROM matches m
                   LEFT JOIN clubs c1 ON m.team1_id = c1.id
                   LEFT JOIN clubs c2 ON m.team2_id = c2.id
                   WHERE (m.team1_id = ? OR m.team2_id = ?) AND m.match_time >= ?
                   ORDER BY m.match_time ASC''',
                (club['id'], club['id'], datetime.now())
            )
            
            matches = [dict(row) for row in cursor.fetchall()]
            
            if not matches:
                await interaction.response.send_message(
                    embed=create_error_embed("You have no upcoming matches!"),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"📅 {club['name']} - Upcoming Matches",
                color=discord.Color.green()
            )
            
            description = ""
            for i, match in enumerate(matches, 1):
                match_time = datetime.fromisoformat(match['match_time']) if isinstance(match['match_time'], str) else match['match_time']
                
                # Determine opponent
                if match['team1_id'] == club['id']:
                    opponent = match['team2_name']
                    vs_text = f"{club['name']} vs **{opponent}**"
                else:
                    opponent = match['team1_name']
                    vs_text = f"**{opponent}** vs {club['name']}"
                
                description += f"{i}. {vs_text}\n"
                description += f"   📅 <t:{int(match_time.timestamp())}:F>\n"
                description += f"   ⏰ <t:{int(match_time.timestamp())}:R>\n\n"
            
            embed.description = description
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting user matches: {e}")
            await interaction.response.send_message(
                embed=create_error_embed(f"Error retrieving your matches: {str(e)}"),
                ephemeral=True
            )
