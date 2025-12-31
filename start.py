"""
Flexible startup script - runs scraper, bot, or both based on RUN_MODE env variable
"""
import os
import sys
import threading
import time

RUN_MODE = os.getenv('RUN_MODE', 'both').lower()

def run_scraper():
    """Run the scraper"""
    print("🔍 Starting dork scraper...")
    try:
        # Import and execute parser.py
        exec(open('parser.py').read())
    except Exception as e:
        print(f"Error running scraper: {e}")
        import traceback
        traceback.print_exc()

def run_telegram_bot():
    """Run the Telegram bot"""
    print("🤖 Starting Telegram bot...")
    try:
        import telegram_bot
        telegram_bot.main()
    except Exception as e:
        print(f"Error running Telegram bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 50)
    print("STARTUP SCRIPT")
    print("=" * 50)
    print(f"Run Mode: {RUN_MODE}")
    print("=" * 50 + "\n")
    
    if RUN_MODE == 'scraper_only':
        print("Running SCRAPER ONLY mode\n")
        run_scraper()
    
    elif RUN_MODE == 'bot_only':
        print("Running TELEGRAM BOT ONLY mode\n")
        run_telegram_bot()
    
    elif RUN_MODE == 'both':
        print("Running BOTH scraper and bot\n")
        # Start scraper in a separate thread
        scraper_thread = threading.Thread(target=run_scraper, daemon=True)
        scraper_thread.start()
        
        # Give scraper a moment to start
        time.sleep(3)
        
        # Run bot in main thread (keeps process alive)
        run_telegram_bot()
    
    else:
        print(f"Invalid RUN_MODE: {RUN_MODE}")
        print("Valid options: scraper_only, bot_only, both")
        sys.exit(1)
