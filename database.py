import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import threading

logger = logging.getLogger(__name__)

# Thread-local storage for database connections
_local = threading.local()

def get_db_connection():
    """Get a thread-local database connection"""
    if not hasattr(_local, 'connection'):
        _local.connection = sqlite3.connect('football_bot.db', check_same_thread=False)
        _local.connection.row_factory = sqlite3.Row
    return _local.connection

def init_database():
    """Initialize the database with all required tables"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Clubs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clubs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                owner_id INTEGER UNIQUE,
                money REAL DEFAULT 0.0,
                role_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Players table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value REAL DEFAULT 0.0,
                position TEXT,
                age INTEGER,
                club_id INTEGER,
                contract_end DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (club_id) REFERENCES clubs (id)
            )
        ''')
        
        # Transfers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                from_club_id INTEGER,
                to_club_id INTEGER NOT NULL,
                transfer_fee REAL DEFAULT 0.0,
                transfer_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player_id) REFERENCES players (id),
                FOREIGN KEY (from_club_id) REFERENCES clubs (id),
                FOREIGN KEY (to_club_id) REFERENCES clubs (id)
            )
        ''')
        
        # Matches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team1_id INTEGER NOT NULL,
                team2_id INTEGER NOT NULL,
                match_time TIMESTAMP NOT NULL,
                reminder_sent BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team1_id) REFERENCES clubs (id),
                FOREIGN KEY (team2_id) REFERENCES clubs (id)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_club ON players(club_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transfers_player ON transfers(player_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_time ON matches(match_time)')
        
        conn.commit()
        logger.info("Database tables initialized")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

# Club management functions
def create_club(name: str, owner_id: int, money: float = 0.0, role_id: Optional[int] = None) -> bool:
    """Create a new club"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO clubs (name, owner_id, money, role_id) VALUES (?, ?, ?, ?)',
            (name, owner_id, money, role_id)
        )
        conn.commit()
        return True
        
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        logger.error(f"Error creating club: {e}")
        return False

def get_club_by_owner(owner_id: int) -> Optional[Dict]:
    """Get club by owner ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM clubs WHERE owner_id = ?', (owner_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
        
    except Exception as e:
        logger.error(f"Error getting club by owner: {e}")
        return None

def get_club_by_name(name: str) -> Optional[Dict]:
    """Get club by name"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM clubs WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None
        
    except Exception as e:
        logger.error(f"Error getting club by name: {e}")
        return None

def get_all_clubs() -> List[Dict]:
    """Get all clubs"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM clubs ORDER BY name')
        return [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        logger.error(f"Error getting all clubs: {e}")
        return []

def update_club_money(club_id: int, money: float) -> bool:
    """Update club money"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE clubs SET money = ? WHERE id = ?', (money, club_id))
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        logger.error(f"Error updating club money: {e}")
        return False

def update_club_role(club_id: int, role_id: Optional[int]) -> bool:
    """Update club role"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE clubs SET role_id = ? WHERE id = ?', (role_id, club_id))
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        logger.error(f"Error updating club role: {e}")
        return False

def delete_club(club_id: int) -> bool:
    """Delete a club and all related data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete transfers
        cursor.execute('DELETE FROM transfers WHERE from_club_id = ? OR to_club_id = ?', (club_id, club_id))
        
        # Delete matches
        cursor.execute('DELETE FROM matches WHERE team1_id = ? OR team2_id = ?', (club_id, club_id))
        
        # Update players to remove club association
        cursor.execute('UPDATE players SET club_id = NULL WHERE club_id = ?', (club_id,))
        
        # Delete club
        cursor.execute('DELETE FROM clubs WHERE id = ?', (club_id,))
        
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        logger.error(f"Error deleting club: {e}")
        return False

# Player management functions
def create_player(name: str, value: float = 0.0, position: Optional[str] = None, age: Optional[int] = None, club_id: Optional[int] = None) -> bool:
    """Create a new player"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO players (name, value, position, age, club_id) VALUES (?, ?, ?, ?, ?)',
            (name, value, position, age, club_id)
        )
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error creating player: {e}")
        return False

def get_player_by_name(name: str) -> Optional[Dict]:
    """Get player by name"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM players WHERE name = ?', (name,))
        row = cursor.fetchone()
        return dict(row) if row else None
        
    except Exception as e:
        logger.error(f"Error getting player by name: {e}")
        return None

def get_players_by_club(club_id: int) -> List[Dict]:
    """Get all players in a club"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM players WHERE club_id = ? ORDER BY value DESC', (club_id,))
        return [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        logger.error(f"Error getting players by club: {e}")
        return []

def get_free_agents() -> List[Dict]:
    """Get all players without a club"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM players WHERE club_id IS NULL ORDER BY value DESC')
        return [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        logger.error(f"Error getting free agents: {e}")
        return []

def update_player_value(player_id: int, value: float) -> bool:
    """Update player value"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE players SET value = ? WHERE id = ?', (value, player_id))
        conn.commit()
        return cursor.rowcount > 0
        
    except Exception as e:
        logger.error(f"Error updating player value: {e}")
        return False

def transfer_player(player_id: int, to_club_id: int, transfer_fee: float = 0.0) -> bool:
    """Transfer a player to a new club"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current club
        cursor.execute('SELECT club_id FROM players WHERE id = ?', (player_id,))
        row = cursor.fetchone()
        from_club_id = row['club_id'] if row else None
        
        # Update player's club
        cursor.execute('UPDATE players SET club_id = ? WHERE id = ?', (to_club_id, player_id))
        
        # Record transfer
        cursor.execute(
            'INSERT INTO transfers (player_id, from_club_id, to_club_id, transfer_fee) VALUES (?, ?, ?, ?)',
            (player_id, from_club_id, to_club_id, transfer_fee)
        )
        
        # Update club finances
        if from_club_id:
            cursor.execute('UPDATE clubs SET money = money + ? WHERE id = ?', (transfer_fee, from_club_id))
        cursor.execute('UPDATE clubs SET money = money - ? WHERE id = ?', (transfer_fee, to_club_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error transferring player: {e}")
        return False

# Match management functions
def create_match(team1_id: int, team2_id: int, match_time: datetime) -> bool:
    """Create a new match"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO matches (team1_id, team2_id, match_time) VALUES (?, ?, ?)',
            (team1_id, team2_id, match_time)
        )
        conn.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error creating match: {e}")
        return False

def get_upcoming_matches(minutes: int = 5) -> List[Dict]:
    """Get matches starting within the specified minutes"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        now = datetime.now()
        future_time = now + timedelta(minutes=minutes)
        
        cursor.execute(
            '''SELECT * FROM matches 
               WHERE match_time BETWEEN ? AND ? 
               AND reminder_sent = FALSE''',
            (now, future_time)
        )
        
        matches = [dict(row) for row in cursor.fetchall()]
        
        # Mark reminders as sent
        if matches:
            match_ids = [match['id'] for match in matches]
            placeholders = ','.join(['?'] * len(match_ids))
            cursor.execute(f'UPDATE matches SET reminder_sent = TRUE WHERE id IN ({placeholders})', match_ids)
            conn.commit()
        
        return matches
        
    except Exception as e:
        logger.error(f"Error getting upcoming matches: {e}")
        return []

# Statistics functions
def get_top_players_by_value(limit: int = 10) -> List[Dict]:
    """Get top players by value"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            '''SELECT p.*, c.name as club_name 
               FROM players p 
               LEFT JOIN clubs c ON p.club_id = c.id 
               ORDER BY p.value DESC 
               LIMIT ?''',
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        logger.error(f"Error getting top players: {e}")
        return []

def get_richest_clubs(limit: int = 10) -> List[Dict]:
    """Get richest clubs"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM clubs ORDER BY money DESC LIMIT ?', (limit,))
        return [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        logger.error(f"Error getting richest clubs: {e}")
        return []

def get_recent_transfers(limit: int = 10) -> List[Dict]:
    """Get recent transfers"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            '''SELECT t.*, p.name as player_name, 
                      c1.name as from_club_name, c2.name as to_club_name
               FROM transfers t
               LEFT JOIN players p ON t.player_id = p.id
               LEFT JOIN clubs c1 ON t.from_club_id = c1.id
               LEFT JOIN clubs c2 ON t.to_club_id = c2.id
               ORDER BY t.transfer_date DESC
               LIMIT ?''',
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
        
    except Exception as e:
        logger.error(f"Error getting recent transfers: {e}")
        return []

def reset_all_data() -> bool:
    """Reset all data in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete all data
        cursor.execute('DELETE FROM transfers')
        cursor.execute('DELETE FROM matches')
        cursor.execute('DELETE FROM players')
        cursor.execute('DELETE FROM clubs')
        
        # Reset auto-increment counters
        cursor.execute('DELETE FROM sqlite_sequence')
        
        conn.commit()
        logger.info("All data reset successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting data: {e}")
        return False
