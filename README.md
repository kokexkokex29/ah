# Football Club Management Discord Bot

A comprehensive Discord bot for managing football clubs, players, transfers, and matches with advanced features like match scheduling, financial management, and detailed statistics.

## Features

### 🏟️ Club Management
- Create and manage football clubs
- Set club finances in Euros
- Track club statistics and rankings
- Compare clubs side-by-side

### ⚽ Player Management
- Create players with positions, ages, and values
- Transfer players between clubs
- Track free agents
- Update player values dynamically

### 💰 Financial System
- Euro-based currency system
- Transfer fees and club budgets
- Financial statistics and rankings
- Automatic transaction handling

### 📅 Match Scheduling
- Schedule matches between clubs
- Automatic DM notifications to team owners
- 5-minute match reminders
- View upcoming matches

### 📊 Statistics & Analytics
- League-wide statistics
- Club rankings by various criteria
- Transfer market analysis
- Player value tracking

### 🔒 Security Features
- Administrator-only command access
- Proper rate limiting to prevent Discord API issues
- Input validation and error handling
- Graceful shutdown handling

## Commands

### Club Commands
- `/create_club` - Create a new football club
- `/club_info` - Show information about a club
- `/list_clubs` - List all clubs
- `/set_club_money` - Set a club's money amount (admin)
- `/delete_club` - Delete a club (admin)
- `/richest_clubs` - Show the richest clubs

### Player Commands
- `/create_player` - Create a new player
- `/player_info` - Show information about a player
- `/set_player_value` - Set a player's market value (admin)
- `/transfer_player` - Transfer a player between clubs (admin)
- `/free_agents` - Show players without a club
- `/club_squad` - Show all players in a club
- `/top_players` - Show the most valuable players
- `/recent_transfers` - Show recent player transfers

### Match Commands
- `/create_match` - Schedule a match between two teams (admin)
- `/upcoming_matches` - Show upcoming matches
- `/my_matches` - Show matches for your club

### Statistics Commands
- `/league_stats` - Show overall league statistics
- `/club_rankings` - Show club rankings by different criteria
- `/transfer_market` - Show transfer market analysis
- `/compare_clubs` - Compare two clubs side by side

### Admin Commands
- `/bot_info` - Show bot information and statistics
- `/reset_all` - Reset all data in the database (DANGEROUS)
- `/create_embed` - Create a custom embed with image support

## Installation & Setup

### Prerequisites
- Python 3.9 or higher
- Discord Bot Token
- Render.com account (for deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd football-club-bot
   ```

2. **Install dependencies**
   ```bash
   pip install discord.py flask aiohttp apscheduler python-dotenv
   