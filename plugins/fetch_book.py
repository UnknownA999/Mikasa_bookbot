import io
import requests
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
        return await message.reply_text("⚠️ Please give me a book name.\nExample: `/fetch Atomic Habits`")
        
    query = message.text.split(" ", 1)[1]
    status_msg = await message.reply_text(f"🔍 Searching the web for **{query}**...\n*(This takes a minute for the first time)*")
    
    s = LibgenSearch()
    try:
        # 1. Search Libgen
        results = s.search_default(query, search_in=[SearchTopic.FICTION, SearchTopic.LIBGEN])
        if not results:
            return await status_msg.edit_text("❌ Couldn't find that book online right now. Check your spelling!")
            
        # 💥 NEW FILTER: Scan results for the English version 💥
        book = None
        for result in results:
            if result.language and 'english' in result.language.lower():
                book = result
                break
        
        # If no English version exists at all, fallback to the top result
        if not book:
            book = results[0] 

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

        await status_msg.edit_text(f"📥 Found **{title}**!\nDownloading to server buffer...")
        
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
      
