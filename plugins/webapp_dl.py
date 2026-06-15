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
        
        # Extract the short 24-character MongoDB ID from the command
        short_id = message.command[1].replace("file_", "")
        
        try:
            # 1. Find the exact document using the short ID
            file_data = await Media.collection.find_one({"_id": ObjectId(short_id)})
        except Exception:
            file_data = None
                
        # If the file was deleted or doesn't exist
        if not file_data:
            await message.reply_text("⚠️ **Sorry, this file is no longer available in our database!**")
            return
            
        # 2. Deliver the file instantly using the massive Telegram file_id stored in the database!
        await client.send_document(
            chat_id=message.chat.id,
            document=file_data["file_id"],
            caption=f"**{file_data.get('file_name', 'Book')}**\n\n⚜️ Powered By : [ Mikasa Library ]"
        )
        
        # We return here so the bot STOPS processing. 
        # This prevents the "You are not verified" message from showing up.
        return 

    # If it's just a normal /start command, we let your other plugins handle it normally.
    raise ContinuePropagation
