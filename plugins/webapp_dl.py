import logging
import re
from pyrogram import Client, filters, StopPropagation, ContinuePropagation
from database.ia_filterdb import Media

# Check if bot uses multiple DBs
try:
    from database.ia_filterdb import Media2
except ImportError:
    Media2 = None
    
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

# group=-1 ensures this runs BEFORE your normal verification and start commands!
@Client.on_message(filters.private & filters.command("start"), group=-1)
async def webapp_deep_link_handler(client, message):
    if len(message.command) > 1 and message.command[1].startswith("file_"):
        
        raw_id = message.command[1].replace("file_", "").strip()
        file_data = None
        
        # Prepare the "Contains" Regex (No ^ symbol, so it matches anywhere in the string)
        safe_search = re.escape(raw_id)
        
        # List of databases to search
        collections_to_search = [Media.collection]
        if Media2 is not None:
            collections_to_search.append(Media2.collection)
            
        for collection in collections_to_search:
            
            # Try 1: Exact Match
            file_data = await collection.find_one({"file_id": raw_id})
            if file_data: break
            
            # Try 2: "Contains" Regex Match (Bypasses prefixes like 8365434970_ and 64-char limits)
            file_data = await collection.find_one({"file_id": {"$regex": safe_search}})
            if file_data: break
            
            # Try 3: Short MongoDB ObjectId Match
            try:
                file_data = await collection.find_one({"_id": ObjectId(raw_id)})
                if file_data: break
            except Exception:
                pass

        # If absolutely nothing is found
        if not file_data:
            await message.reply_text(f"⚠️ **Sorry, this file is no longer available!**\n\n`(Debug: {raw_id})`")
            raise StopPropagation
            
        # Deliver the full, valid file instantly!
        await client.send_document(
            chat_id=message.chat.id,
            document=file_data["file_id"],
            caption=f"**{file_data.get('file_name', 'Book')}**\n\n⚜️ Powered By : [ Mikasa Library ]"
        )
        
        # Stops Fsub and the 16-hour verification from running!
        raise StopPropagation

    # Normal /start commands continue to the next handlers
    raise ContinuePropagation
