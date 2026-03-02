import io
import aiohttp
import re
import asyncio
from pyrogram import Client, filters
from libgen_api_enhanced import LibgenSearch, SearchTopic
from database.ia_filterdb import save_file, Media 

BIN_CHANNEL_ID = -1003793921200 # ⚠️ REPLACE WITH YOUR ACTUAL BIN CHANNEL ID

class MockMedia:
    def __init__(self, document, message):
        self.file_id = document.file_id
        self.file_name = document.file_name
        self.file_size = document.file_size
        self.file_type = "document"
        self.mime_type = document.mime_type
        self.caption = message.caption

# 💥 Background search function so the bot doesn't freeze
async def async_search(s, query):
    return await asyncio.to_thread(s.search_default, query, search_in=[SearchTopic.FICTION, SearchTopic.LIBGEN])

@Client.on_message(filters.command("fetch"))
async def fetch_book_on_demand(client, message):
    if len(message.command) == 1:
        return await message.reply_text(
            "⚠️ Please give me a book name.\n\n"
            "**Examples:**\n"
            "1. Default (English): `/fetch Atomic Habits`\n"
            "2. Specific Language: `/fetch Atomic Habits lang:spanish`"
        )
        
    raw_query = message.text.split(" ", 1)[1]
    
    lang_match = re.search(r'lang:([a-zA-Z]+)', raw_query, re.IGNORECASE)
    if lang_match:
        target_lang = lang_match.group(1).lower()
        search_query = re.sub(r'lang:[a-zA-Z]+', '', raw_query, flags=re.IGNORECASE).strip()
    else:
        target_lang = "english"
        search_query = raw_query.strip()

    status_msg = await message.reply_text(f"🔍 Searching the web for **{search_query}** ({target_lang.capitalize()})...")
    
    s = LibgenSearch()
    try:
        # Use the new async search
        results = await async_search(s, search_query)
        if not results:
            return await status_msg.edit_text("❌ Couldn't find that book online right now. Check your spelling!")
            
        book = None
        for result in results:
            if result.language and target_lang in result.language.lower():
                book = result
                break
        
        if not book:
            book = results[0] 
            actual_lang = book.language or "Unknown"
            await status_msg.edit_text(f"⚠️ Couldn't find a **{target_lang.capitalize()}** version.\n📥 Downloading the **{actual_lang}** version instead...")
        else:
            await status_msg.edit_text(f"📥 Found **{book.title}** ({target_lang.capitalize()})!\nDownloading to server buffer...")

        title = book.title
        author = book.author
        ext = book.extension
        lang = book.language or "Unknown"
        
        clean_title = title.replace("/", "-").replace(":", "")
        custom_file_name = f"{clean_title} by {author} [{lang}] @Bookhubz.{ext}"

        exists = await Media.count_documents({"file_name": custom_file_name}, limit=1)
        if exists:
            return await status_msg.edit_text(f"✅ **{clean_title}** is already in our database!\n\nJust search for it normally.")
        
        try:
            await asyncio.to_thread(book.resolve_direct_download_link)
            direct_link = book.resolved_download_link
            if not direct_link:
                return await status_msg.edit_text("❌ Found the book, but the download link is broken.")
        except Exception:
            return await status_msg.edit_text("❌ Failed to resolve the download link.")
            
        # 💥 ASYNC DOWNLOADING (No more freezing!)
        headers = {'User-Agent': 'Mozilla/5.0'}
        async with aiohttp.ClientSession() as session:
            async with session.get(direct_link, headers=headers, timeout=30) as response:
                if response.status != 200:
                    return await status_msg.edit_text("❌ Failed to download the file from the source.")
                content = await response.read()
                file_in_ram = io.BytesIO(content)
                
        file_in_ram.name = custom_file_name
        
        await status_msg.edit_text("📤 Uploading book to Bookhubz Library...")
        
        sent_msg = await client.send_document(
            chat_id=BIN_CHANNEL_ID,
            document=file_in_ram,
            caption=f"📚 **{clean_title}**\n👤 {author}\n🌐 Language: {lang}\n\nAdded on-demand to #Bookhubz"
        )
        
        media_obj = MockMedia(sent_msg.document, sent_msg)
        saved, status = await save_file(media_obj)
        
        if saved:
            await status_msg.edit_text(f"🎉 **Success!**\n\n**{clean_title}** has been permanently added to the library.\n\nType the name normally to get your file!")
        else:
            await status_msg.edit_text("⚠️ Sent to channel, but there was a minor issue indexing it to the database.")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ An error occurred: `{str(e)}`")
