import asyncio
import io
import requests
from pyrogram import Client
from libgen_api_enhanced import LibgenSearch, SearchTopic
# 💥 IMPORTING YOUR BOT'S NATIVE DATABASE HANDLERS 💥
from database.ia_filterdb import save_file, Media 

BIN_CHANNEL_ID = -1003793921200 # Your Bookhubz Bin channel ID

# 💥 THE POPULAR GENRE HARVEST LIST 💥
POPULAR_GENRES = [
    "Psychological Thriller", "Philosophy", "Classic Literature", 
    "Manga", "Light Novel", "Manhwa", "Comic", "Graphic Novel",
    "Mystery", "Science Fiction", "Fantasy", "Romance", 
    "Self-Help", "Historical Fiction", "Horror", "Crime", 
    "Business", "Biography", "True Crime", "Dystopian"
]

# A small wrapper to make the document compatible with your save_file() logic
class MockMedia:
    def __init__(self, document, message):
        self.file_id = document.file_id
        self.file_name = document.file_name
        self.file_size = document.file_size
        self.file_type = "document"
        self.mime_type = document.mime_type
        self.caption = message.caption

async def background_book_scraper(app: Client, db):
    print("🤖 Background Library Builder Started (SAFE HARVEST MODE)...")
    s = LibgenSearch()
    
    while True: # Infinite loop to keep it running 24/7
        for query in POPULAR_GENRES:
            try:
                # Search Fiction database first
                results = s.search_default(query, search_in=[SearchTopic.FICTION, SearchTopic.LIBGEN])
                if not results:
                    continue
                    
                for book in results[:15]: # Grab top 15 books per genre
                    title = book.title
                    author = book.author
                    ext = book.extension
                    lang = book.language or "Unknown"
                    
                    # 💥 NEW: Skip non-English books 💥
                    if 'english' not in lang.lower():
                        continue
                    
                    # Clean the title exactly how your bot expects
                    clean_title = title.replace("/", "-").replace(":", "")

                    
                    # Clean the title exactly how your bot expects
                    clean_title = title.replace("/", "-").replace(":", "")
                    custom_file_name = f"{clean_title} by {author} [{lang}] @Bookhubz.{ext}"

                    # 1. SMART CHECK: See if your bot already has this exact filename
                    exists = await Media.count_documents({"file_name": custom_file_name}, limit=1)
                    if exists:
                        continue

                    # 2. Get the direct, ad-free download link
                    try:
                        book.resolve_direct_download_link()
                        direct_link = book.resolved_download_link
                        if not direct_link:
                            continue
                    except Exception as e:
                        print(f"⚠️ Skip: Could not resolve link for {title}")
                        continue

                    # 3. Stream to RAM (Zero Disk Usage!)
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    response = requests.get(direct_link, stream=True, headers=headers, timeout=30)
                    if response.status_code != 200:
                        continue
                        
                    file_in_ram = io.BytesIO(response.content)
                    
                    # 4. Rename exactly how you want it
                    file_in_ram.name = custom_file_name

                    # 5. Upload to Bin Channel
                    sent_msg = await app.send_document(
                        chat_id=BIN_CHANNEL_ID,
                        document=file_in_ram,
                        caption=f"📚 **{clean_title}**\n👤 {author}\nAdded automatically to #Bookhubz"
                    )

                    # 6. SAVE TO YOUR NATIVE DATABASE
                    media_obj = MockMedia(sent_msg.document, sent_msg)
                    saved, status = await save_file(media_obj)
                    
                    if saved:
                        print(f"✅ Added & Indexed: {custom_file_name}")
                    else:
                        print(f"⚠️ Sent to channel, but DB skip/error code: {status}")

                    # 💥 PLAYING IT SAFE: 2 Minute Sleep 💥
                    await asyncio.sleep(120)

            except Exception as e:
                print(f"Scraper Error on '{query}': {e}")
                await asyncio.sleep(60)
