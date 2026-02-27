import io
import requests
import re
from pyrogram import Client, filters
from libgen_api_enhanced import LibgenSearch, SearchTopic
from database.ia_filterdb import save_file, Media 

BIN_CHANNEL_ID = -1003793921200 # ⚠️ REPLACE WITH YOUR ACTUAL BIN CHANNEL ID

# Wrapper to make the file compatible with your native database logic
class MockMedia:
    def __init__(self, document, message):
        self.file_id = document.file_id
        self.file_name = document.file_name
        self.file_size = document.file_size
        self.file_type = "document"
        self.mime_type = document.mime_type
        self.caption = message.caption

@Client.on_message(filters.command("fetch"))
async def fetch_book_on_demand(client, message):
    # Check if they actually typed a book name
    if len(message.command) == 1:
        return await message.reply_text(
            "⚠️ Please give me a book name.\n\n"
            "**Examples:**\n"
            "1. Default (English): `/fetch Atomic Habits`\n"
            "2. Specific Language: `/fetch Atomic Habits lang:spanish`"
        )
        
    raw_query = message.text.split(" ", 1)[1]
    
    # 💥 BULLETPROOF LANGUAGE PARSER 💥
    # Looks for "lang:spanish", "lang:hindi", etc.
    lang_match = re.search(r'lang:([a-zA-Z]+)', raw_query, re.IGNORECASE)
    if lang_match:
        target_lang = lang_match.group(1).lower()
        # Remove the "lang:xxx" part from the search query so Libgen searches properly
        search_query = re.sub(r'lang:[a-zA-Z]+', '', raw_query, flags=re.IGNORECASE).strip()
    else:
        target_lang = "english" # Default
        search_query = raw_query.strip()

    status_msg = await message.reply_text(f"🔍 Searching the web for **{search_query}** ({target_lang.capitalize()})...\n*(This takes a minute for the first time)*")
    
    s = LibgenSearch()
    try:
        # 1. Search Libgen
        results = s.search_default(search_query, search_in=[SearchTopic.FICTION, SearchTopic.LIBGEN])
        if not results:
            return await status_msg.edit_text("❌ Couldn't find that book online right now. Check your spelling!")
            
        # 💥 DYNAMIC LANGUAGE FILTER 💥
        book = None
        for result in results:
            if result.language and target_lang in result.language.lower():
                book = result
                break
        
        # If the specific language isn't found, fallback to the top result
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
        
        # Format the name
        clean_title = title.replace("/", "-").replace(":", "")
        custom_file_name = f"{clean_title} by {author} [{lang}] @Bookhubz.{ext}"

        # 2. Check your DB first (in case someone else already fetched it)
        exists = await Media.count_documents({"file_name": custom_file_name}, limit=1)
        if exists:
            return await status_msg.edit_text(f"✅ **{clean_title}** is already in our database!\n\nJust search for it normally.")
        
        # 3. Resolve the direct link safely
        try:
            book.resolve_direct_download_link()
            direct_link = book.resolved_download_link
            if not direct_link:
                return await status_msg.edit_text("❌ Found the book, but the download link is broken.")
        except Exception:
            return await status_msg.edit_text("❌ Failed to resolve the download link.")
            
        # 4. Stream to RAM (Zero Disk Usage!)
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(direct_link, stream=True, headers=headers, timeout=30)
        if response.status_code != 200:
            return await status_msg.edit_text("❌ Failed to download the file from the source.")
            
        file_in_ram = io.BytesIO(response.content)
        file_in_ram.name = custom_file_name
        
        await status_msg.edit_text("📤 Uploading book to Bookhubz Library...")
        
        # 5. Upload to Bin Channel
        sent_msg = await client.send_document(
            chat_id=BIN_CHANNEL_ID,
            document=file_in_ram,
            caption=f"📚 **{clean_title}**\n👤 {author}\n🌐 Language: {lang}\n\nAdded on-demand to #Bookhubz"
        )
        
        # 6. Save to your native AutoFilter Database
        media_obj = MockMedia(sent_msg.document, sent_msg)
        saved, status = await save_file(media_obj)
        
        if saved:
            await status_msg.edit_text(f"🎉 **Success!**\n\n**{clean_title}** has been permanently added to the library.\n\nType the name normally to get your file!")
        else:
            await status_msg.edit_text("⚠️ Sent to channel, but there was a minor issue indexing it to the database.")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ An error occurred: `{str(e)}`")
