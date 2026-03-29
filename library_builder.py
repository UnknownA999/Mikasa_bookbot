import asyncio
import io
import aiohttp
from pyrogram import Client
from libgen_api_enhanced import LibgenSearch, SearchTopic
from database.ia_filterdb import save_file, Media 

BIN_CHANNEL_ID = -1003793921200 # Your Bookhubz Bin channel ID

POPULAR_GENRES = [
    "Psychological Thriller", "Philosophy", "Classic Literature", 
    "Manga", "Light Novel", "Manhwa", "Comic", "Graphic Novel",
    "Mystery", "Science Fiction", "Fantasy", "Romance", 
    "Self-Help", "Historical Fiction", "Horror", "Crime", 
    "Business", "Biography", "True Crime", "Dystopian"
]

class MockMedia:
    def __init__(self, document, message):
        self.file_id = document.file_id
        self.file_name = document.file_name
        self.file_size = document.file_size
        self.file_type = "document"
        self.mime_type = document.mime_type
        self.caption = message.caption

# 💥 This forces the Libgen search into a background thread so the bot doesn't freeze!
async def async_search(s, query):
    return await asyncio.to_thread(s.search_default, query, search_in=[SearchTopic.FICTION, SearchTopic.LIBGEN])

import os

async def background_book_scraper(app: Client, db):
    print("🤖 Background Library Builder Started (LOW-RAM DISK MODE)...")
    s = LibgenSearch()
    
    # Ensure a local downloads folder exists
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    while True: 
        for query in POPULAR_GENRES:
            try:
                results = await async_search(s, query)
                if not results:
                    await asyncio.sleep(10) # Short wait before next genre
                    continue
                    
                for book in results[:15]:
                    title = book.title
                    author = book.author
                    ext = book.extension
                    lang = book.language or "Unknown"
                    
                    if 'english' not in lang.lower():
                        continue
                    
                    clean_title = title.replace("/", "-").replace(":", "")
                    custom_file_name = f"{clean_title} by {author} [{lang}] @mikasa_network.{ext}"
                    local_file_path = os.path.join("downloads", custom_file_name)

                    exists = await Media.count_documents({"file_name": custom_file_name}, limit=1)
                    if exists:
                        continue

                    try:
                        # Resolve link in background thread
                        await asyncio.to_thread(book.resolve_direct_download_link)
                        direct_link = book.resolved_download_link
                        if not direct_link:
                            continue
                    except Exception as e:
                        print(f"Link resolution error: {e}")
                        continue

                    # 💥 NEW: ASYNC DOWNLOADING TO DISK IN CHUNKS
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(direct_link, headers=headers, timeout=60) as response:
                            if response.status != 200:
                                continue
                            
                            # Write file to disk in 1MB chunks instead of holding it in RAM
                            with open(local_file_path, 'wb') as f:
                                async for chunk in response.content.iter_chunked(1024 * 1024):
                                    f.write(chunk)
                    
                    # Upload the physical file to Telegram
                    sent_msg = await app.send_document(
                        chat_id=BIN_CHANNEL_ID,
                        document=local_file_path,
                        caption=f"📚 **{clean_title}**\n👤 {author}\nAdded automatically to #Bookhubz"
                    )

                    # 💥 NEW: Delete the file immediately to save server storage
                    if os.path.exists(local_file_path):
                        os.remove(local_file_path)

                    media_obj = MockMedia(sent_msg.document, sent_msg)
                    saved, status = await save_file(media_obj)
                    
                    if saved:
                        print(f"✅ Added & Indexed: {custom_file_name}")

                    # Standard rest between downloads
                    await asyncio.sleep(60)

            except Exception as e:
                print(f"Scraper Error on '{query}': {e}")
                # 💥 NEW: Smart back-off for Cloudflare blocks
                if "Verification" in str(e):
                    print("🛑 Hit Libgen anti-bot verification. Resting for 5 minutes...")
                    await asyncio.sleep(300) 
                else:
                    await asyncio.sleep(60)
            
            # Rest between genres to avoid triggering limits
            await asyncio.sleep(30)
