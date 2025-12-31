import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '7780407325:AAFAVFkIRm0aYFLbVeTrwMz_vXJ1YMeMrrs')
URLS_FILE = 'jphq.txt'
PROGRESS_FILE = 'progress.json'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        '👋 Hello! I\'m your Dork Scraper Bot.\n\n'
        'Commands:\n'
        '/send - Send the URLs file\n'
        '/status - Get scraping status\n'
        '/help - Show this help message'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        '📋 Available Commands:\n\n'
        '/send - Download the scraped URLs file (jphq.txt)\n'
        '/status - Check scraping progress and stats\n'
        '/start - Start the bot\n'
        '/help - Show this message'
    )

async def send_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the URLs file when /send is issued."""
    try:
        if not os.path.exists(URLS_FILE):
            await update.message.reply_text(
                '⚠️ No URLs file found yet.\n'
                'The scraper may not have started or found any URLs.'
            )
            return
        
        # Get file size
        file_size = os.path.getsize(URLS_FILE)
        file_size_mb = file_size / (1024 * 1024)
        
        # Count lines
        with open(URLS_FILE, 'r', encoding='utf-8') as f:
            line_count = sum(1 for line in f if line.strip())
        
        await update.message.reply_text(
            f'📤 Sending file...\n'
            f'Size: {file_size_mb:.2f} MB\n'
            f'URLs: {line_count:,}'
        )
        
        # Send the file
        with open(URLS_FILE, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=URLS_FILE,
                caption=f'✅ {line_count:,} URLs scraped'
            )
        
        logger.info(f"Sent file to user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await update.message.reply_text(
            f'❌ Error sending file: {str(e)}'
        )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send scraping status when /status is issued."""
    try:
        status_msg = "📊 Scraper Status:\n\n"
        
        # Check if URLs file exists
        if os.path.exists(URLS_FILE):
            file_size = os.path.getsize(URLS_FILE)
            file_size_mb = file_size / (1024 * 1024)
            
            with open(URLS_FILE, 'r', encoding='utf-8') as f:
                line_count = sum(1 for line in f if line.strip())
            
            status_msg += f"✅ URLs File: Found\n"
            status_msg += f"📝 Total URLs: {line_count:,}\n"
            status_msg += f"💾 File Size: {file_size_mb:.2f} MB\n"
        else:
            status_msg += "⚠️ URLs File: Not found\n"
        
        # Check progress
        if os.path.exists(PROGRESS_FILE):
            import json
            try:
                with open(PROGRESS_FILE, 'r') as f:
                    progress = json.load(f)
                    last_completed = progress.get('last_completed', 0)
                    status_msg += f"\n🔄 Progress:\n"
                    status_msg += f"Last dork completed: #{last_completed}\n"
            except:
                pass
        
        await update.message.reply_text(status_msg)
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await update.message.reply_text(
            f'❌ Error getting status: {str(e)}'
        )

def main():
    """Start the bot."""
    logger.info("Starting Telegram bot...")
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("send", send_file))
    application.add_handler(CommandHandler("status", status))
    
    # Start the Bot
    logger.info("Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
