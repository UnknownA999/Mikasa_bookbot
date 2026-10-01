import asyncio
from pyrogram import Client, filters
from info import ADMINS, WEB_HUB
from utils import temp

@Client.on_message(filters.command("batch") & filters.user(ADMINS))
async def create_batch(client, message):
    try:
        links = message.text.split(" ")
        if len(links) != 3:
            return await message.reply("⚠️ **Format:** `/batch [first_file_link] [last_file_link]`")
        
        # Extract message IDs from your private channel links
        first_msg_id = int(links[1].split("/")[-1])
        last_msg_id = int(links[2].split("/")[-1])
        
        if first_msg_id > last_msg_id:
            first_msg_id, last_msg_id = last_msg_id, first_msg_id

        # Generate the Web Hub Deep Link with Monetag Redirection
        batch_link = f"{WEB_HUB}?start=batch_{first_msg_id}_{last_msg_id}&bot={temp.U_NAME}"
        
        await message.reply(
            f"✅ **Batch Link Generated!**\n\n"
            f"🔗 `{batch_link}`\n\n"
            f"*(This link is monetized. Users will see an ad before getting the files in Telegram.)*",
            disable_web_page_preview=True
        )
    except Exception as e:
        await message.reply(f"❌ **Error:** {e}\n\nMake sure you are using valid channel links.")



import re
from pyrogram import Client, filters
from info import ADMINS, WEB_HUB

# Auto-Converter for Old Links (Only for Admins)
@Client.on_message(filters.private & filters.regex(r"https?://(?:t\.me|telegram\.me)/([a-zA-Z0-9_]+)\?start=([a-zA-Z0-9_-]+)") & filters.user(ADMINS))
async def update_old_link(client, message):
    # Link se bot ka naam aur start parameter (jaise batch_3611_3611) nikalna
    match = message.matches[0]
    bot_username = match.group(1)
    start_param = match.group(2)
    
    # Naya Web Hub link generate karna
    new_link = f"{WEB_HUB}?start={start_param}&bot={bot_username}"
    
    await message.reply_text(
        f"✅ **Updated Monetized Link:**\n\n"
        f"🔗 `{new_link}`\n\n"
        f"*(Copy and paste this in your channels!)*",
        disable_web_page_preview=True
    )

