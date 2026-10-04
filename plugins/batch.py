import asyncio
from pyrogram import Client, filters
from info import ADMINS
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

        # Generate the deep link
        batch_link = f"https://t.me/{temp.U_NAME}?start=batch_{first_msg_id}_{last_msg_id}"
        
        await message.reply(
            f"✅ **Batch Link Generated!**\n\n"
            f"🔗 `{batch_link}`",
            disable_web_page_preview=True
        )

    except Exception as e:
        await message.reply(f"❌ **Error:** {e}\n\nMake sure you are using valid channel links.")



import re
from pyrogram import Client, filters
from info import ADMINS


# Smart Auto-Converter for ANY old link (Only for Admins)
@Client.on_message(filters.private & filters.regex(r"start=([a-zA-Z0-9_-]+)") & filters.user(ADMINS))
async def update_old_link(client, message):
    # Link mein se sirf main ID (start parameter) nikalna
    start_param = message.matches[0].group(1)
    
    # Naya Native Telegram link generate karna
    new_link = f"https://t.me/{temp.U_NAME}?start={start_param}"
    
    await message.reply_text(
        f"✅ **Updated Native Telegram Link:**\n\n"
        f"🔗 `{new_link}`\n\n"
        f"*(You can replace your old Web Hub links with this!)*",
        disable_web_page_preview=True
    )


