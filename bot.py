import os
import logging
import time
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes as CT
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


last_req_time = 0


def download_image(query):
    """Download image from DuckDuckGo and save locally"""
    global last_req_time
    import requests
    
    # Wait between requests
    current_time = time.time()
    if current_time - last_req_time < 12:
        wait = 12 - (current_time - last_req_time)
        time.sleep(wait)
    
    last_req_time = time.time()
    
    try:
        from ddgs import DDGS
        
        ddgs = DDGS()
        results = list(ddgs.images(query, max_results=50, safesearch='off'))
        
        if results:
            logger.info(f"Found {len(results)} images for: {query}")
            
            # Try up to 5 different images
            for i in range(min(5, len(results))):
                img_data = results[i]
                img_url = img_data.get('image') or img_data.get('url') or img_data.get('href')
                
                if img_url:
                    try:
                        logger.info(f"Trying to download image {i+1}: {img_url[:80]}...")
                        # Download image
                        response = requests.get(img_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                        logger.info(f"Download response: {response.status_code}")
                        if response.status_code == 200:
                            # Save to temp file
                            temp_path = f"temp_{i}.jpg"
                            with open(temp_path, 'wb') as f:
                                f.write(response.content)
                            logger.info(f"Successfully downloaded: {temp_path}")
                            return temp_path
                    except Exception as e:
                        logger.warning(f"Failed to download image {i+1}: {e}")
                        continue
            
            return None
        
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None


async def handle_message(update: Update, context: CT.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    
    if text.startswith('%') and len(text) > 1:
        query = text[1:].strip()
        
        if query:
            await context.bot.send_chat_action(
                chat_id=update.message.chat_id,
                action='typing'
            )
            
            logger.info("Starting download...")
            img_path = download_image(query)
            logger.info(f"Download result: {img_path}")
            
            if img_path:
                try:
                    logger.info("Opening file...")
                    with open(img_path, 'rb') as photo:
                        logger.info("Sending photo...")
                        await context.bot.send_photo(
                            chat_id=update.message.chat_id,
                            photo=photo,
                            caption=f"По запросу: {query}"
                        )
                        logger.info("Photo sent successfully")
                    
                    # Clean up
                    import os
                    os.remove(img_path)
                    logger.info("Temp file removed")
                except Exception as e:
                    logger.error(f"Error sending: {e}")
                    await update.message.reply_text(f"Ошибка отправки")
            else:
                await update.message.reply_text(
                    f"Не найдено изображений для '{query}'"
                )


async def start(update: Update, context: CT.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Напиши %запрос и получи картинку!\nПример: %арбуз"
    )


def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
