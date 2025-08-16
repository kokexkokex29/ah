# Football Club Management Discord Bot

## Overview

This is a comprehensive Discord bot for managing football clubs, players, transfers, and matches. The system provides a complete fantasy football management experience through Discord slash commands, featuring club creation, player management, financial systems, match scheduling, and detailed statistics. The bot is designed for administrator-controlled environments where server admins manage all aspects of the football league.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
The application follows a modular command-based architecture using Discord.py's Cogs system. Core components include:

- **Bot Core**: Main bot class (`FootballBot`) that inherits from `commands.Bot` with proper intents configuration for guild and member access
- **Command Modules**: Organized into separate Cogs for different functionality areas:
  - `AdminCommands`: System administration and data management
  - `ClubCommands`: Football club creation and management
  - `PlayerCommands`: Player creation, transfers, and value management
  - `MatchCommands`: Match scheduling and notifications
  - `StatsCommands`: Analytics and league statistics

### Data Storage
- **Database**: SQLite database with thread-local connections for concurrent access
- **Schema Design**: Relational structure with tables for clubs, players, transfers, and matches
- **Data Integrity**: Foreign key relationships and proper transaction handling

### Security & Permissions
- **Administrator-Only Access**: All commands restricted to Discord users with administrator permissions
- **Permission Validation**: Centralized permission checking through utility functions
- **Input Validation**: Comprehensive validation for all user inputs and database operations

### Web Interface
- **Flask Web Server**: Simple status dashboard showing bot operational state
- **Bootstrap UI**: Dark-themed responsive interface with status indicators
- **Real-time Updates**: JavaScript-based status polling for live bot monitoring

### Rate Limiting & API Management
- **Discord API Rate Limiting**: Custom rate limit handler with connection pooling
- **Graceful Error Handling**: Proper exception handling and user feedback
- **Connection Management**: Thread-local database connections and session management

### Background Tasks
- **Match Notifications**: Automated Discord DM notifications for upcoming matches
- **Reminder System**: 5-minute match reminders with background task scheduling
- **Keep-Alive Mechanism**: Web server keeps the bot active on hosting platforms

### Financial System
- **Euro-based Currency**: All financial transactions in Euros with proper decimal handling
- **Transfer System**: Complete player transfer workflow with financial validation
- **Budget Management**: Club budget tracking and transaction history

## External Dependencies

### Discord Integration
- **discord.py**: Primary Discord API wrapper for bot functionality
- **Slash Commands**: Modern Discord interaction system using app_commands

### Web Framework
- **Flask**: Lightweight web server for status monitoring
- **Bootstrap 5**: Frontend CSS framework with dark theme support
- **Font Awesome**: Icon library for enhanced UI elements

### Database
- **SQLite**: Embedded database for data persistence
- **Thread-safe Operations**: Connection pooling for concurrent access

### HTTP Client
- **aiohttp**: Asynchronous HTTP client for external API calls and rate limiting

### Utilities
- **asyncio**: Asynchronous programming support for Discord bot operations
- **threading**: Thread-local storage for database connections
- **logging**: Comprehensive logging system for debugging and monitoring

### Hosting Requirements
- **Environment Variables**: `DISCORD_TOKEN` for bot authentication
- **File System**: Persistent storage for SQLite database file
- **Network Access**: HTTPS support for Discord webhook operations