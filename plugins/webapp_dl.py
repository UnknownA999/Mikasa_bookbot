import logging
from pyrogram import Client, filters, ContinuePropagation
from database.ia_filterdb import Media
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

# group=-1 ensures this runs BEFORE your normal verification and start commands!
@Client.on_message(filters.private & filters.command("start"), group=-1)
async def webapp_deep_link_handler(client, message):
    # Check if this is a download link from our Mini App
    if len(message.command) > 1 and message.command[1].startswith("file_"):
        
        # Extract the ID from the command
        file_id_string = message.command[1].replace("file_", "")
        
        # 1. Search the database
        file_data = await Media.collection.find_one({"file_id": file_id_string})
        
        # 2. Fallback: If it's a raw MongoDB ObjectId, search by _id
        if not file_data:
            try:
                file_data = await Media.collection.find_one({"_id": ObjectId(file_id_string)})
            except Exception:
                pass
                
        # If the file was deleted or doesn't exist
        if not file_data:
            await message.reply_text("⚠️ **Sorry, this file is no longer available in our database!**")
            return
            
        # 3. Deliver the file instantly! (Bypasses verification)
        await client.send_cached_media(
            chat_id=message.chat.id,
            file_id=file_data["file_id"],
            caption=f"**{file_data.get('file_name', 'Book')}**\n\n⚜️ Powered By : [ Mikasa Library ]"
        )
        
        # We return here so the bot STOPS processing. 
        # This prevents the "You are not verified" message from showing up.
        return 

    # If it's just a normal /start command, we let your other plugins handle it normally.
    raise ContinuePropagation
