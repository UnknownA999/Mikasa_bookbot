import logging
from pyrogram import Client, filters, ContinuePropagation
from database.ia_filterdb import Media
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

# group=-1 ensures this runs BEFORE your normal verification and start commands!
@Client.on_message(filters.private & filters.command("start"), group=-1)
async def webapp_deep_link_handler(client, message):
    if len(message.command) > 1 and message.command[1].startswith("file_"):
        
        # Extract whatever ID the WebApp sent us (even if it's chopped in half)
        short_id = message.command[1].replace("file_", "")
        file_data = None
        
        # Try 1: Is it a short MongoDB ObjectId?
        try:
            file_data = await Media.collection.find_one({"_id": ObjectId(short_id)})
        except Exception:
            pass
            
        # Try 2: Is it a custom string ID?
        if not file_data:
            try:
                file_data = await Media.collection.find_one({"_id": short_id})
            except Exception:
                pass
                
        # Try 3: THE BULLETPROOF FIX
        # If Telegram chopped the massive file_id in half, we search for a file that STARTS with the chopped text!
        if not file_data:
            try:
                file_data = await Media.collection.find_one({"file_id": {"$regex": f"^{short_id}"}})
            except Exception:
                pass

        # If it still fails, it prints a debug code so we know exactly what went wrong.
        if not file_data:
            await message.reply_text(f"⚠️ **Sorry, this file is no longer available!**\n\n`(Debug Code: {short_id})`")
            return
            
        # Deliver the full, un-chopped file instantly!
        await client.send_document(
            chat_id=message.chat.id,
            document=file_data["file_id"],
            caption=f"**{file_data.get('file_name', 'Book')}**\n\n⚜️ Powered By : [ Mikasa Library ]"
        )
        
        return # Stops the bot from showing the 16-hour verification text

    # Normal /start commands continue as normal
    raise ContinuePropagation
