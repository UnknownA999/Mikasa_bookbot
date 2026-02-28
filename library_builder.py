import asyncio
import io
import aiohttp # 💥 The new, non-blocking downloader
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

# 💥 NEW: This forces the Libgen search into a background thread so the bot doesn't freeze
async def async_search(s, query):
    return await asyncio.to_thread(s.search_default, query, search_in=[SearchTopic.FICTION, SearchTopic.LIBGEN])

async def background_book_scraper(app: Client, db):
    print("🤖 Background Library Builder Started (FAST ASYNC MODE)...")
    s = LibgenSearch()
    
    while True: 
        for query in POPULAR_GENRES:
            try:
                # Use the new background search
                results = await async_search(s, query)
                if not results:
                    continue
                    
                for book in results[:15]:
                    title = book.title
                    author = book.author
                    ext = book.extension
                    lang = book.language or "Unknown"
                    
                    if 'english' not in lang.lower():
                        continue
                    
                    clean_title = title.replace("/", "-").replace(":", "")
                    custom_file_name = f"{clean_title} by {author} [{lang}] @Bookhubz.{ext}"

                    exists = await Media.count_documents({"file_name": custom_file_name}, limit=1)
                    if exists:
                        continue

                    try:
                        # Resolve link in background thread
                        await asyncio.to_thread(book.resolve_direct_download_link)
                        direct_link = book.resolved_download_link
                        if not direct_link:
                            continue
                    except Exception:
                        continue

                    # 💥 NEW: Async Downloading! This lets the bot answer users WHILE downloading
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    async with aiohttp.ClientSession() as session:
                        async with session.get(direct_link, headers=headers, timeout=30) as response:
                            if response.status != 200:
                                continue
                            content = await response.read()
                            file_in_ram = io.BytesIO(content)
                    
                    file_in_ram.name = custom_file_name

                    sent_msg = await app.send_document(
                        chat_id=BIN_CHANNEL_ID,
                        document=file_in_ram,
                        caption=f"📚 **{clean_title}**\n👤 {author}\nAdded automatically to #Bookhubz"
                    )

                    media_obj = MockMedia(sent_msg.document, sent_msg)
                    saved, status = await save_file(media_obj)
                    
                    if saved:
                        print(f"✅ Added & Indexed: {custom_file_name}")

                    await asyncio.sleep(120)

            except Exception as e:
                print(f"Scraper Error on '{query}': {e}")
                await asyncio.sleep(60)
