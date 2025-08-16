import os
import asyncio
import logging
from typing import Optional
import discord
from discord.ext import commands, tasks
from utils.rate_limiter import RateLimitHandler
from utils.permissions import is_administrator
from commands.admin import AdminCommands
from commands.clubs import ClubCommands
from commands.players import PlayerCommands
from commands.matches import MatchCommands
from commands.stats import StatsCommands

logger = logging.getLogger(__name__)

class FootballBot(commands.Bot):
    def __init__(self):
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
            case_insensitive=True,
            max_messages=1000
        )
        
        # Rate limiting handler
        self.rate_limiter = RateLimitHandler()
        
        # Track if bot is ready
        self.bot_ready = False
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        try:
            # Add command cogs
            await self.add_cog(AdminCommands(self))
            await self.add_cog(ClubCommands(self))
            await self.add_cog(PlayerCommands(self))
            await self.add_cog(MatchCommands(self))
            await self.add_cog(StatsCommands(self))
            
            # Start background tasks
            self.check_match_reminders.start()
            
            logger.info("Bot setup completed")
            
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
            
    async def on_ready(self):
        """Called when the bot has successfully connected to Discord"""
        try:
            logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
            logger.info(f"Connected to {len(self.guilds)} guilds")
            
            # Sync slash commands
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
            
            # Set bot status
            await self.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name="football clubs"
                ),
                status=discord.Status.online
            )
            
            self.bot_ready = True
            logger.info("Bot is ready!")
            
        except Exception as e:
            logger.error(f"Error in on_ready: {e}")
            
    async def on_error(self, event_method: str, *args, **kwargs):
        """Handle errors in event handlers"""
        logger.error(f"Error in {event_method}", exc_info=True)
        
    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
            
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
            return
            
        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send("❌ I don't have the required permissions to execute this command.")
            return
            
        logger.error(f"Command error in {ctx.command}: {error}", exc_info=True)
        await ctx.send("❌ An error occurred while executing the command.")
        
    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Handle slash command errors"""
        if isinstance(error, discord.app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return
            
        if isinstance(error, discord.app_commands.BotMissingPermissions):
            await interaction.response.send_message("❌ I don't have the required permissions to execute this command.", ephemeral=True)
            return
            
        logger.error(f"Slash command error: {error}", exc_info=True)
        
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while executing the command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while executing the command.", ephemeral=True)
        except:
            pass
            
    @tasks.loop(minutes=1)
    async def check_match_reminders(self):
        """Check for upcoming matches and send reminders"""
        try:
            from database import get_upcoming_matches
            
            upcoming_matches = get_upcoming_matches(minutes=5)
            
            for match in upcoming_matches:
                try:
                    from database import get_db_connection
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    # Get team details including role_id
                    cursor.execute('SELECT * FROM clubs WHERE id = ?', (match['team1_id'],))
                    team1_data = dict(cursor.fetchone())
                    
                    cursor.execute('SELECT * FROM clubs WHERE id = ?', (match['team2_id'],))
                    team2_data = dict(cursor.fetchone())
                    
                    # Create reminder embed
                    embed = discord.Embed(
                        title="⚽ Match Reminder",
                        description=f"Your match is starting in 5 minutes!",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Teams", value=f"{team1_data['name']} vs {team2_data['name']}", inline=False)
                    embed.add_field(name="Time", value=f"<t:{int(match['match_time'].timestamp())}:F>", inline=False)
                    
                    # Send to team1 role members
                    if team1_data.get('role_id'):
                        for guild in self.guilds:
                            team1_role = guild.get_role(team1_data['role_id'])
                            if team1_role:
                                for member in team1_role.members:
                                    try:
                                        await member.send(embed=embed)
                                    except discord.Forbidden:
                                        logger.warning(f"Could not send DM to {member}")
                                break
                    else:
                        # Fallback to owner
                        team1_owner = self.get_user(team1_data['owner_id'])
                        if team1_owner:
                            try:
                                await team1_owner.send(embed=embed)
                            except discord.Forbidden:
                                logger.warning(f"Could not send DM to {team1_owner}")
                    
                    # Send to team2 role members
                    if team2_data.get('role_id'):
                        for guild in self.guilds:
                            team2_role = guild.get_role(team2_data['role_id'])
                            if team2_role:
                                for member in team2_role.members:
                                    try:
                                        await member.send(embed=embed)
                                    except discord.Forbidden:
                                        logger.warning(f"Could not send DM to {member}")
                                break
                    else:
                        # Fallback to owner
                        team2_owner = self.get_user(team2_data['owner_id'])
                        if team2_owner and team2_owner.id != team1_data['owner_id']:
                            try:
                                await team2_owner.send(embed=embed)
                            except discord.Forbidden:
                                logger.warning(f"Could not send DM to {team2_owner}")
                                
                except Exception as e:
                    logger.error(f"Error sending match reminder: {e}")
                    
        except Exception as e:
            logger.error(f"Error in check_match_reminders: {e}")
            
    @check_match_reminders.before_loop
    async def before_check_match_reminders(self):
        """Wait until the bot is ready before starting the reminder loop"""
        await self.wait_until_ready()
        
    async def close(self):
        """Clean shutdown"""
        try:
            # Cancel background tasks
            if hasattr(self, 'check_match_reminders'):
                self.check_match_reminders.cancel()
                
            # Close rate limiter
            if hasattr(self, 'rate_limiter'):
                await self.rate_limiter.close()
                
            # Close bot
            await super().close()
            logger.info("Bot closed successfully")
            
        except Exception as e:
            logger.error(f"Error during bot shutdown: {e}")
