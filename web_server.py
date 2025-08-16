import os
import logging
import threading
import asyncio
import time
import random
from flask import Flask, render_template, jsonify

logger = logging.getLogger(__name__)

# قفل وفلاغ للتأكد أن البوت يشتغل مرة واحدة فقط
bot_started = False
bot_lock = threading.Lock()

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "football-bot-secret-key")

    # Initialize database
    try:
        from database import init_database
        init_database()
        logger.info("Database initialized for Flask app")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    async def start_bot_with_retry(bot, token, retries=5):
        """Start bot with retry logic to handle rate limits"""
        delay = 5
        for attempt in range(retries):
            try:
                logger.info(f"Starting Discord bot (attempt {attempt+1})...")
                await bot.start(token)
                return
            except Exception as e:
                logger.error(f"Bot start failed (attempt {attempt+1}): {e}")
                if attempt < retries - 1:
                    wait = delay + random.randint(0,5)
                    logger.info(f"Retrying in {wait} seconds...")
                    await asyncio.sleep(wait)
                    delay *= 2
                else:
                    logger.error("Max retries reached, bot failed to start.")

    def start_discord_bot():
        """Start Discord bot in a separate thread"""
        global bot_started
        with bot_lock:
            if bot_started:
                logger.info("Discord bot already running, skipping startup.")
                return
            bot_started = True

        try:
            logger.info("Waiting 30 seconds before starting bot to avoid rate limiting...")
            time.sleep(30)

            from bot import FootballBot
            discord_token = os.getenv("DISCORD_TOKEN")
            if not discord_token:
                logger.warning("DISCORD_TOKEN not found - bot will not start")
                return

            bot = FootballBot()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start_bot_with_retry(bot, discord_token))

        except Exception as e:
            logger.error(f"Error starting Discord bot: {e}")

    # Start bot in a background thread
    bot_thread = threading.Thread(target=start_discord_bot, daemon=True)
    bot_thread.start()

    # ------------------ Flask Routes ------------------

    @app.route('/')
    def index():
        """Main status page"""
        return render_template('index.html')

    @app.route('/status')
    def status():
        """API endpoint for bot status"""
        try:
            from database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as count FROM clubs')
            club_count = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(*) as count FROM players')
            player_count = cursor.fetchone()['count']

            cursor.execute('SELECT COUNT(*) as count FROM transfers')
            transfer_count = cursor.fetchone()['count']

            return jsonify({
                'status': 'online',
                'database': 'connected',
                'stats': {
                    'clubs': club_count,
                    'players': player_count,
                    'transfers': transfer_count
                }
            })

        except Exception as e:
            logger.error(f"Status check error: {e}")
            return jsonify({
                'status': 'error',
                'database': 'disconnected',
                'error': str(e)
            }), 500

    @app.route('/health')
    def health():
        """Health check endpoint for Render.com / UptimeRobot"""
        return jsonify({'status': 'healthy'}), 200

    return app
