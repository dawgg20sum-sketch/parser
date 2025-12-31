"""
Combined script that runs both the dork scraper and Telegram bot
"""
import threading
import time
import sys
import os

def run_scraper():
    """Run the scraper in a separate thread"""
    print("🔍 Starting dork scraper...")
    try:
        import parser
    except Exception as e:
        print(f"Error running scraper: {e}")

def run_telegram_bot():
    """Run the Telegram bot in a separate thread"""
    # Wait a bit for scraper to start
    time.sleep(2)
    print("🤖 Starting Telegram bot...")
    try:
        import telegram_bot
        telegram_bot.main()
    except Exception as e:
        print(f"Error running Telegram bot: {e}")

if __name__ == '__main__':
    print("=" * 50)
    print("STARTING COMBINED SERVICE")
    print("=" * 50)
    print("This will run:")
    print("1. Dork Scraper (parser.py)")
    print("2. Telegram Bot (telegram_bot.py)")
    print("=" * 50 + "\n")
    
    # Start scraper in a separate thread
    scraper_thread = threading.Thread(target=run_scraper, daemon=False)
    scraper_thread.start()
    
    # Start Telegram bot in main thread
    run_telegram_bot()
