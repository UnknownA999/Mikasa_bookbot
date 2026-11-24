import os
import random
import string
from pyrogram import enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.users_chats_db import db
from utils import get_shortlink, temp
from info import TUTORIAL, VERIFY_IMG

# 🔘 MASTER SWITCH: Jab hatana ho bas ise False kar dena (ya Render env se control karo)
ENABLE_SHORTENER = os.environ.get("ENABLE_SHORTENER", "True").lower() == "true"

# ⏱️ Verification Validity (Seconds mein)
# 57600 = 16 Hours | 86400 = 24 Hours
VERIFY_TIME = 57600 


async def check_shortener_gate(client, message, data):
    """
    Returns: (is_allowed: bool, updated_data: str)
    Agar False return hua, toh commands.py wahin ruk jayega.
    """
    if not ENABLE_SHORTENER:
        return True, data

    user_id = message.from_user.id

    # 1. VERIFICATION COMPLETION CHECK
    if data.startswith(("notcopy_", "sendall_", "verify_")):
        try:
            parts = data.split("_", 3)
            req_user_id = parts[1]
            if str(user_id) != str(req_user_id):
                await message.reply_text("⚠️ **This verification link is not for you!**")
                return False, None

            await db.update_verify_status(user_id)
            await message.reply_text(
                "✅ **Verification Successful!**\n\n"
                "You now have direct access to all files for the next **16 hours**. Enjoy! ✨"
            )

            # Original file/batch command wapas restore karna
            if data.startswith("sendall_"):
                return True, f"allfiles_0_{parts[3]}"
            elif data.startswith("notcopy_"):
                return True, f"file_0_{parts[3]}"
            else:
                return True, parts[3]
        except Exception as e:
            await message.reply_text(f"❌ Verification Error: {e}")
            return False, None

    # 2. VERIFICATION GATE (Single File, Send All, aur Batch ke liye)
    if data.startswith(("file_", "allfiles_", "batch_")):
        if not await db.has_premium_access(user_id):
            user_verified = await db.is_user_verified(user_id)
            time_expired = await db.use_second_shortener(user_id, VERIFY_TIME)

            if not user_verified or time_expired:
                verify_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
                await db.create_verify_id(user_id, verify_id)
                temp.VERIFICATIONS[user_id] = message.chat.id

                if data.startswith(("allfiles_", "batch_")):
                    actual_key = data.split("_", 2)[2] if len(data.split("_")) > 2 else data
                    verify_url = f"https://telegram.me/{temp.U_NAME}?start=sendall_{user_id}_{verify_id}_{actual_key}"
                else:
                    actual_file_id = data.split("_", 2)[2] if len(data.split("_")) > 2 else data
                    verify_url = f"https://telegram.me/{temp.U_NAME}?start=notcopy_{user_id}_{verify_id}_{actual_file_id}"

                try:
                    short_url = await get_shortlink(verify_url, message.chat.id, False, False)
                except Exception:
                    short_url = verify_url

                buttons = [
                    [InlineKeyboardButton("♻️ ᴄʟɪᴄᴋ ʜᴇʀᴇ ᴛᴏ ᴠᴇʀɪꜰʏ ♻️", url=short_url)],
                    [InlineKeyboardButton("⁉️ ʜᴏᴡ ᴛᴏ ᴠᴇʀɪꜰʏ ⁉️", url=TUTORIAL)],
                    [InlineKeyboardButton("⭐ ɢᴏ ᴀᴅ-ꜰʀᴇᴇ / ʙᴜʏ ᴘʀᴇᴍɪᴜᴍ ⭐", callback_data="premium_info")]
                ]

                await message.reply_photo(
                    photo=VERIFY_IMG,
                    caption=(
                        f"📌 **{message.from_user.mention}, ʏᴏᴜ ᴀʀᴇ ɴᴏᴛ ᴠᴇʀɪꜰɪᴇᴅ!**\n\n"
                        f"ᴘʟᴇᴀꜱᴇ ᴄᴏᴍᴘʟᴇᴛᴇ ᴀ ǫᴜɪᴄᴋ 1-ᴘᴀɢᴇ ᴠᴇʀɪꜰɪᴄᴀᴛɪᴏɴ ᴛᴏ ᴜɴʟᴏᴄᴋ ᴜɴʟɪᴍɪᴛᴇᴅ ᴅɪʀᴇᴄᴛ ꜰɪʟᴇꜱ ꜰᴏʀ **16 ʜᴏᴜʀꜱ**."
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                    parse_mode=enums.ParseMode.HTML
                )
                return False, None

    return True, data
          
