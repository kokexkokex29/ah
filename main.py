import os
import asyncio
import logging
import signal
import threading
from flask import Flask
from bot import FootballBot
from web_server import create_app
from database import init_database

# Create Flask app for gunicorn
app = create_app()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        self.bot = None
        self.flask_app = None
        self.shutdown_event = asyncio.Event()
        
    async def start_bot(self):
        """Start the Discord bot with proper error handling"""
        try:
            # Initialize database
            logger.info("Initializing database...")
            init_database()
            
            # Create bot instance
            logger.info("Creating bot instance...")
            self.bot = FootballBot()
            
            # Start bot
            logger.info("Starting Discord bot...")
            discord_token = os.getenv("DISCORD_TOKEN")
            if not discord_token:
                raise ValueError("DISCORD_TOKEN environment variable is required")
                
            await self.bot.start(discord_token)
            
        except Exception as e:
            logger.error(f"Bot error: {e}")
            self.shutdown_event.set()
            
    async def start_web_server(self):
        """Start the Flask web server in a separate thread"""
        try:
            logger.info("Starting web server...")
            self.flask_app = create_app()
            
            def run_flask():
                self.flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
            
            flask_thread = threading.Thread(target=run_flask, daemon=True)
            flask_thread.start()
            logger.info("Web server started on port 5000")
            
        except Exception as e:
            logger.error(f"Web server error: {e}")
            
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down...")
        self.shutdown_event.set()
        
        if self.bot:
            try:
                await self.bot.close()
                logger.info("Bot closed successfully")
            except Exception as e:
                logger.error(f"Error closing bot: {e}")
                
    async def run(self):
        """Main run loop"""
        try:
            # Start web server
            await self.start_web_server()
            
            # Start bot
            bot_task = asyncio.create_task(self.start_bot())
            
            # Wait for shutdown signal
            shutdown_task = asyncio.create_task(self.shutdown_event.wait())
            
            # Wait for either bot to finish or shutdown signal
            done, pending = await asyncio.wait(
                [bot_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            await self.shutdown()

def signal_handler(manager):
    """Handle shutdown signals"""
    def handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(manager.shutdown())
    return handler

async def main():
    """Main entry point"""
    manager = BotManager()
    
    # Setup signal handlers
    handler = signal_handler(manager)
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    
    try:
        await manager.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        logger.info("Application terminated")

if __name__ == "__main__":
    asyncio.run(main())
