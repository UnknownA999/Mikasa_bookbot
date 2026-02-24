import time
import re
import os
from pyrogram import Client, filters, enums
from info import BIN_CHANNEL
from database.users_chats_db import db
from Script import script

upload_cooldown = {}
ALLOWED_EXTENSIONS = ['.pdf', '.epub', '.mobi', '.cbz', '.zip']

@Client.on_message(filters.private & filters.document)
async def contribute_file(client, message):
    user_id = message.from_user.id
    current_time = time.time()
    
    # 1. Cooldown Check
    last_time = upload_cooldown.get(user_id, 0)
    if current_time - last_time < 30:
        return await message.reply_text("⏳ **Cooldown Active!** Please wait 30 seconds between uploads.")

    file_name = message.document.file_name
    if not file_name:
        return await message.reply_text("❌ **Error:** Please send a valid document file.")

    # 2. Extension Check
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return await message.reply_text(
            f"❌ **Invalid Format!** I only accept `PDF, EPUB, MOBI, CBZ, ZIP`.\nYou sent a `{ext}` file."
        )

    # 3. Naming Check
    pattern = r".+ by .+ \[.+\].*" 
    if not re.match(pattern, file_name, re.IGNORECASE):
        return await message.reply_text(
            script.CONTRIBUTION_TUTORIAL, 
            parse_mode=enums.ParseMode.HTML
        )

    # 4. Forward and Award Points
    upload_cooldown[user_id] = current_time
    # Forward the file to the Bin Channel for indexing
    await message.forward(BIN_CHANNEL)
    
    # 5. Add Points using our new safe database function
    await db.add_contribution(user_id)
    
    await message.reply_text("✅ **Contribution Accepted!** Thank you for sharing knowledge. Check /my_profile!")
      
