import logging
import re
from pyrogram import Client, filters, StopPropagation, ContinuePropagation
from database.ia_filterdb import Media
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

# group=-1 ensures this runs BEFORE your normal verification and start commands!
@Client.on_message(filters.private & filters.command("start"), group=-1)
async def webapp_deep_link_handler(client, message):
    if len(message.command) > 1 and message.command[1].startswith("file_"):
        
        # Take the exact ID Telegram gives us (even if it's chopped at 64 chars)
        raw_id = message.command[1].replace("file_", "")
        file_data = None
        
        # Try 1: The Ultimate Regex Fix
        # We search the database for any file_id that STARTS WITH the chopped text
        try:
            safe_search = re.escape(raw_id)
            file_data = await Media.collection.find_one({"file_id": {"$regex": f"^{safe_search}"}})
        except Exception:
            pass
            
        # Try 2: Is it a short MongoDB ObjectId? (Future-proofing for when you update route.py)
        if not file_data:
            try:
                file_data = await Media.collection.find_one({"_id": ObjectId(raw_id)})
            except Exception:
                pass
                
        # Try 3: Raw match fallback
        if not file_data:
            try:
                file_data = await Media.collection.find_one({"file_id": raw_id})
            except Exception:
                pass

        if not file_data:
            await message.reply_text(f"⚠️ **Sorry, this file is no longer available!**\n\n`(Debug: {raw_id})`")
            raise StopPropagation
            
        # Deliver the full, un-chopped file instantly!
        await client.send_document(
            chat_id=message.chat.id,
            document=file_data["file_id"],
            caption=f"**{file_data.get('file_name', 'Book')}**\n\n⚜️ Powered By : [ Mikasa Library ]"
        )
        
        # Stops Fsub and the 16-hour verification from running!
        raise StopPropagation

    # Normal /start commands continue to the next handlers
    raise ContinuePropagation
