import discord
from typing import Optional, List, Dict

def create_club_embed(club: Dict) -> discord.Embed:
    """Create an embed for club information"""
    embed = discord.Embed(
        title=f"🏟️ {club['name']}",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="💰 Balance",
        value=f"€{club['money']:,.2f}",
        inline=True
    )
    
    embed.add_field(
        name="👤 Owner",
        value=f"<@{club['owner_id']}>",
        inline=True
    )
    
    embed.add_field(
        name="📅 Founded",
        value=f"<t:{int(club['created_at'].timestamp()) if hasattr(club['created_at'], 'timestamp') else 0}:D>",
        inline=True
    )
    
    return embed

def create_player_embed(player: Dict, club_name: Optional[str] = None) -> discord.Embed:
    """Create an embed for player information"""
    embed = discord.Embed(
        title=f"⚽ {player['name']}",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="💎 Value",
        value=f"€{player['value']:,.2f}",
        inline=True
    )
    
    if player.get('position'):
        embed.add_field(
            name="🎯 Position",
            value=player['position'],
            inline=True
        )
    
    if player.get('age'):
        embed.add_field(
            name="🎂 Age",
            value=f"{player['age']} years",
            inline=True
        )
    
    if club_name:
        embed.add_field(
            name="🏟️ Club",
            value=club_name,
            inline=True
        )
    elif player.get('club_id') is None:
        embed.add_field(
            name="🏟️ Club",
            value="Free Agent",
            inline=True
        )
    
    return embed

def create_transfer_embed(transfer: Dict) -> discord.Embed:
    """Create an embed for transfer information"""
    embed = discord.Embed(
        title="🔄 Transfer Completed",
        color=discord.Color.orange()
    )
    
    embed.add_field(
        name="⚽ Player",
        value=transfer.get('player_name', 'Unknown'),
        inline=False
    )
    
    if transfer.get('from_club_name'):
        embed.add_field(
            name="📤 From",
            value=transfer['from_club_name'],
            inline=True
        )
    else:
        embed.add_field(
            name="📤 From",
            value="Free Agent",
            inline=True
        )
    
    embed.add_field(
        name="📥 To",
        value=transfer.get('to_club_name', 'Unknown'),
        inline=True
    )
    
    embed.add_field(
        name="💰 Fee",
        value=f"€{transfer['transfer_fee']:,.2f}",
        inline=True
    )
    
    return embed

def create_match_embed(match: Dict, team1_name: str, team2_name: str) -> discord.Embed:
    """Create an embed for match information"""
    embed = discord.Embed(
        title="⚽ Football Match",
        color=discord.Color.red()
    )
    
    embed.add_field(
        name="🆚 Teams",
        value=f"{team1_name} vs {team2_name}",
        inline=False
    )
    
    embed.add_field(
        name="📅 Date & Time",
        value=f"<t:{int(match['match_time'].timestamp())}:F>",
        inline=False
    )
    
    embed.add_field(
        name="⏰ Countdown",
        value=f"<t:{int(match['match_time'].timestamp())}:R>",
        inline=False
    )
    
    return embed

def create_stats_embed(title: str, data: List[Dict], value_field: str, name_field: str = 'name') -> discord.Embed:
    """Create a generic stats embed"""
    embed = discord.Embed(
        title=title,
        color=discord.Color.purple()
    )
    
    if not data:
        embed.description = "No data available."
        return embed
    
    description = ""
    for i, item in enumerate(data[:10], 1):
        name = item.get(name_field, 'Unknown')
        value = item.get(value_field, 0)
        
        if value_field in ['money', 'value', 'transfer_fee']:
            value_str = f"€{value:,.2f}"
        else:
            value_str = str(value)
            
        description += f"{i}. **{name}** - {value_str}\n"
    
    embed.description = description
    return embed

def create_error_embed(message: str) -> discord.Embed:
    """Create an error embed"""
    embed = discord.Embed(
        title="❌ Error",
        description=message,
        color=discord.Color.red()
    )
    return embed

def create_success_embed(message: str) -> discord.Embed:
    """Create a success embed"""
    embed = discord.Embed(
        title="✅ Success",
        description=message,
        color=discord.Color.green()
    )
    return embed
