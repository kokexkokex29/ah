import os
import logging
import threading
import asyncio
import time
from flask import Flask, render_template, jsonify

logger = logging.getLogger(__name__)

# قفل وفلاغ علشان نتأكد البوت يشتغل مرة وحدة فقط
bot_started = False
bot_lock = threading.Lock()


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "football-bot-secret-key")

    # Initialize database when Flask app is created
    try:
        from database import init_database
        init_database()
        logger.info("Database initialized for Flask app")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    def start_discord_bot():
        """Start Discord bot in a separate thread"""
        global bot_started
        with bot_lock:
            if bot_started:
                logger.info("Discord bot already running, skipping startup.")
                return
            bot_started = True

        try:
            # Wait to avoid initial rate limiting on new deployments
            logger.info("Waiting 30 seconds before starting bot to avoid rate limiting...")
            time.sleep(30)

            from bot import FootballBot
            discord_token = os.getenv("DISCORD_TOKEN")
            if discord_token:
                logger.info("Starting Discord bot...")
                bot = FootballBot()

                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Start the bot
                loop.run_until_complete(bot.start(discord_token))
            else:
                logger.warning("DISCORD_TOKEN not found - bot will not start")
        except Exception as e:
            logger.error(f"Error starting Discord bot: {e}")

    # Start bot in background thread
    bot_thread = threading.Thread(target=start_discord_bot, daemon=True)
    bot_thread.start()

    @app.route('/')
    def index():
        """Main status page"""
        return render_template('index.html')

    @app.route('/status')
    def status():
        """API endpoint for bot status"""
        try:
            from database import get_db_connection

            # Test database connection
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
