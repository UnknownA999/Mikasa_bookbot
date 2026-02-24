from utils import get_size, is_subscribed, is_req_subscribed, group_setting_buttons, get_poster, get_posterx, temp, get_settings, save_group_settings, get_cap, imdb, is_check_admin, extract_request_content, log_error, clean_filename, generate_season_variations, clean_search_text
import tracemalloc
import logging
from database.ia_filterdb import Media, Media2, get_file_details, get_search_results
from database.config_db import mdb
from pyrogram.errors import MessageNotModified
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from info import *
from Script import script
import asyncio
import re
import math
import random
import pytz
from datetime import datetime, timedelta

lock = asyncio.Lock()
logger = logging.getLogger(__name__)
tracemalloc.start()

# --- DYNAMIC DATABASE CHECKER ---
async def fetch_library_options(chat_id, search_query):
    """Analyzes files to find available Volumes, Formats, and Languages."""
    files, _, _ = await get_search_results(chat_id, search_query, max_results=200, filter=True)
    available = {"formats": set(), "languages": set(), "volumes": set()}
    if not files: return available

    for file in files:
        name = file.file_name.lower()
        for fmt in QUALITIES: # QUALITIES now holds PDF, EPUB, etc.
            if fmt.lower() in name: available["formats"].add(fmt)
        for disp_name, code in LANGUAGES.items():
            if code.lower() in name: available["languages"].add(disp_name)
        vol_match = re.search(r'\b(?:vol|volume)\s?0*(\d+)\b', name)
        if vol_match: available["volumes"].add(int(vol_match.group(1)))
    return available

@Client.on_message(filters.text & filters.incoming & ~filters.regex(r"^/"))
async def library_router(bot, message):
    """Routes searches from groups and PM to the auto_filter."""
    if message.chat.type == enums.ChatType.PRIVATE:
        if await db.pm_search_status(bot.me.id):
            await auto_filter(bot, message)
        else:
            await message.reply_text("<b>ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴏᴜʀ ʟɪʙʀᴀʀʏ ɢʀᴏᴜᴘ ᴛᴏ sᴇᴀʀᴄʜ ʙᴏᴏᴋs!</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📝 ᴊᴏɪɴ ʟɪʙʀᴀʀʏ", url=GRP_LNK)]]))
    else:
        await auto_filter(bot, message)

async def auto_filter(client, msg, spoll=False):
    """Core search logic updated for Books and Manga."""
    if not spoll:
        search = msg.text.lower()
        if len(search) > 100: return
        
        # UI: Library Searching Sticker
        m = await msg.reply_sticker("CAACAgIAAxkBAAEPhm5o439f8A4sUGO2VcnBFZRRYxAxmQACtCMAAphLKUjeub7NKlvk2TYE", 
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f'🔎 sᴇᴀʀᴄʜɪɴɢ ʟɪʙʀᴀʀʏ...', callback_data="hiding")]]))
        
        # Clean query: Remove movie terms, keep book terms
        search = re.sub(r"\b(pls|give|send|book|manga|vol|volume|pdf|epub|mobi)\b", "", search, flags=re.IGNORECASE)
        search = re.sub(r"\s+", " ", search).strip()
        
        files, offset, total = await get_search_results(msg.chat.id, search, offset=0, filter=True)
        if not files:
            await m.delete()
            return await msg.reply_text(script.I_CUDNT.format(search))
    else:
        msg = msg.message.reply_to_message
        search, files, offset, total = spoll

    key = f"{msg.chat.id}-{msg.id}"
    temp.GETALL[key] = files
    
    # UI: Format, Language, Volume Buttons
    btn = [
        [InlineKeyboardButton("📁 ꜰᴏʀᴍᴀᴛ", callback_data=f"qualities#{key}"),
         InlineKeyboardButton("🌐 ʟᴀɴɢᴜᴀɢᴇ", callback_data=f"languages#{key}"),
         InlineKeyboardButton("📚 ᴠᴏʟᴜᴍᴇ", callback_data=f"seasons#{key}")],
        [InlineKeyboardButton("🚀 sᴇɴᴅ ᴀʟʟ", callback_data=f"sendfiles#{key}")]
    ]

    settings = await get_settings(msg.chat.id)
    if settings.get('button'):
        for file in files[:10]:
            btn.append([InlineKeyboardButton(text=f"📄 {get_size(file.file_size)} ≽ {clean_filename(file.file_name)}", callback_data=f'file#{file.file_id}')])

    cap = f"<b>📚 ᴛɪᴛʟᴇ: <code>{search.title()}</code>\n📦 ᴛᴏᴛᴀʟ ꜰᴏᴜɴᴅ: <code>{total}</code></b>"
    await msg.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))
    if not spoll: await m.delete()

@Client.on_callback_query(filters.regex(r"^qualities#"))
async def format_handler(client, query):
    _, key = query.data.split("#")
    search = (temp.GETALL.get(key)[0].file_name if temp.GETALL.get(key) else "book").lower()
    await query.answer("🔄 Checking Formats...")
    options = await fetch_library_options(query.message.chat.id, search)
    available = sorted(list(options["formats"]), key=lambda x: QUALITIES.index(x) if x in QUALITIES else 99)
    
    btn = [[InlineKeyboardButton("⇊ sᴇʟᴇᴄᴛ ꜰᴏʀᴍᴀᴛ ⇊", callback_data="ident")]]
    for i in range(0, len(available), 2):
        row = [InlineKeyboardButton(available[i], callback_data=f"fq#{available[i].lower()}#{key}")]
        if i+1 < len(available):
            row.append(InlineKeyboardButton(available[i+1], callback_data=f"fq#{available[i+1].lower()}#{key}"))
        btn.append(row)
    btn.append([InlineKeyboardButton("↭ ʙᴀᴄᴋ", callback_data=f"fq#homepage#{key}")])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(btn))

@Client.on_callback_query(filters.regex(r"^seasons#"))
async def volume_handler(client, query):
    _, key = query.data.split("#")
    search = "book"
    await query.answer("🔄 Checking Volumes...")
    options = await fetch_library_options(query.message.chat.id, search)
    available = sorted(list(options["volumes"]))
    
    btn = [[InlineKeyboardButton("⇊ sᴇʟᴇᴄᴛ ᴠᴏʟᴜᴍᴇ ⇊", callback_data="ident")]]
    for i in range(0, len(available), 3):
        row = [InlineKeyboardButton(f"Vol {available[j]}", callback_data=f"fs#vol{available[j]}#{key}") for j in range(i, min(i+3, len(available)))]
        btn.append(row)
    btn.append([InlineKeyboardButton("↭ ʙᴀᴄᴋ", callback_data=f"next_{query.from_user.id}_{key}_0")])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(btn))
    
