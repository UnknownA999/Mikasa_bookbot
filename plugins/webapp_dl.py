import logging
from pyrogram import Client, filters, StopPropagation, ContinuePropagation
from database.ia_filterdb import Media
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

# group=-1 ensures this runs BEFORE your normal verification and start commands!
@Client.on_message(filters.private & filters.command("start"), group=-1)
async def webapp_deep_link_handler(client, message):
    if len(message.command) > 1 and message.command[1].startswith("file_"):
        
        raw_id = message.command[1].replace("file_", "")
        file_data = None
        
        # Extract the real Telegram file_id (the part after the underscore)
        search_id = raw_id.split("_")[-1] if "_" in raw_id else raw_id
        
        # Try 1: Search by the exact extracted file_id
        try:
            file_data = await Media.collection.find_one({"file_id": search_id})
        except Exception:
            pass
            
        # Try 2: Regex search (if Telegram chopped the 64-char limit)
        if not file_data:
            try:
                file_data = await Media.collection.find_one({"file_id": {"$regex": f"^{search_id}"}})
            except Exception:
                pass
                
        # Try 3: Search the raw string just in case
        if not file_data:
            try:
                file_data = await Media.collection.find_one({"_id": raw_id})
            except Exception:
                pass

        if not file_data:
            await message.reply_text(f"⚠️ **Sorry, this file is no longer available!**\n\n`(Debug: {search_id})`")
            # Stop Fsub from crashing even if file isn't found
            raise StopPropagation
            
        # Deliver the full, un-chopped file instantly!
        await client.send_document(
            chat_id=message.chat.id,
            document=file_data["file_id"],
            caption=f"**{file_data.get('file_name', 'Book')}**\n\n⚜️ Powered By : [ Mikasa Library ]"
        )
        
        # CRITICAL FIX: This absolutely stops Fsub and the 16-hour verification from running!
        raise StopPropagation

    # Normal /start commands continue to the next handlers
    raise ContinuePropagation
