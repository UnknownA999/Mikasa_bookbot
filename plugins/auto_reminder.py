import asyncio
import random
import logging
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from database.users_chats_db import db # Tumhare existing database handler ka use karenge[span_0](start_span)[span_0](end_span)
from utils import temp # Username uthane ke liye[span_1](start_span)[span_1](end_span)

logger = logging.getLogger(__name__)

# Tum yahan apne hisaab se jitne chaho reminders add kar sakte ho!
REMINDER_MESSAGES = [
    "🍿 <b>Weekend is here!</b> Need something to watch?\n\nSearch for any Movie, Web Series, or K-Drama right now!",
    "📚 <b>Boring day?</b> Dive into a new world!\n\nSearch for your favorite Novels, or Academic Books in our library.",
    "🎬 <b>Missed the latest releases?</b>\n\nWe've got them all. Just type the name of the movie or show or even novels and enjoy!",
    "✨ <b>Did you know?</b>\n\nWe have a massive collection of Anime,drama, movies webseries and TV Shows. Send a name to start searching!"
]

# Interval set karo (Seconds mein)
# Example: 3 Days = 3 * 24 * 60 * 60 = 259200 seconds
# Abhi ke liye maine 3 din (259200) set kiya hai. Test karne ke liye ise 60 (1 min) kar sakte ho.
INTERVAL_SECONDS = 259200

async def start_reminder_loop(client: Client):
    logger.info("Auto-Reminder system started in background!")
    
    while True:
        # Pehle wait karega, taaki bot restart hote hi sabko spam na kare
        await asyncio.sleep(INTERVAL_SECONDS)
        
        logger.info("Sending Auto-Reminders to all users...")
        msg_text = random.choice(REMINDER_MESSAGES)
        
        # Bot ka username dynamically lena
        bot_username = temp.U_NAME if hasattr(temp, 'U_NAME') else client.me.username
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Now", url=f"https://t.me/{bot_username}")]
        ])
        
        success = 0
        failed = 0
        
        # Saare users nikal kar loop chalayenge[span_2](start_span)[span_2](end_span)
        users = await db.get_all_users() 
        async for user in users:
            try:
                await client.send_message(
                    chat_id=user['id'],
                    text=msg_text,
                    reply_markup=reply_markup
                )
                success += 1
                await asyncio.sleep(0.5)  # Telegram ki spam limit (FloodWait) se bachne ke liye safe delay
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
                try:
                    await client.send_message(chat_id=user['id'], text=msg_text, reply_markup=reply_markup)
                    success += 1
                except:
                    failed += 1
            except Exception:
                failed += 1
                
        logger.info(f"✅ Reminder Broadcast Done. Success: {success} | Failed: {failed}")
