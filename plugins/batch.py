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
