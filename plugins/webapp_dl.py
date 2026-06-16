import logging
import re
from pyrogram import Client, filters, StopPropagation, ContinuePropagation
from database.ia_filterdb import Media

# Check if bot uses multiple DBs
try:
    from database.ia_filterdb import Media2
except ImportError:
    Media2 = None
    
logger = logging.getLogger(__name__)

# group=-1 ensures this runs BEFORE your normal verification and start commands!
@Client.on_message(filters.private & filters.command("start"), group=-1)
async def webapp_deep_link_handler(client, message):
    if len(message.command) > 1 and message.command[1].startswith("file_"):
        
        raw_id = message.command[1].replace("file_", "").strip()
        file_data = None
        safe_search = re.escape(raw_id)
        
        collections_to_search = [Media.collection]
        if Media2 is not None:
            collections_to_search.append(Media2.collection)
            
        for collection in collections_to_search:
            
            # Try 1: Search the raw _id column (This is where your bot actually stores the ID!)
            file_data = await collection.find_one({"_id": raw_id})
            if file_data: break
            
            # Try 2: Search _id as a Regex (In case Telegram chopped the link at 64 characters)
            file_data = await collection.find_one({"_id": {"$regex": f"^{safe_search}"}})
            if file_data: break
            
            # Try 3: Search file_id as a fallback
            file_data = await collection.find_one({"file_id": raw_id})
            if file_data: break
            
            # Try 4: Search file_id as a Regex fallback
            file_data = await collection.find_one({"file_id": {"$regex": f"^{safe_search}"}})
            if file_data: break

        # If absolutely nothing is found
        if not file_data:
            await message.reply_text(f"⚠️ **Sorry, this file is no longer available!**\n\n`(Debug: {raw_id})`")
            raise StopPropagation
            
        # CRITICAL FIX: Extract the valid Telegram ID from either the file_id or _id column
        telegram_id = file_data.get("file_id") or file_data.get("_id")
        
        # Deliver the full, valid file instantly!
        await client.send_document(
            chat_id=message.chat.id,
            document=telegram_id,
            caption=f"**{file_data.get('file_name', 'Book')}**\n\n⚜️ Powered By : [ Mikasa Library ]"
        )
        
        # Stops Fsub and the 16-hour verification from running!
        raise StopPropagation

    # Normal /start commands continue to the next handlers
    raise ContinuePropagation
