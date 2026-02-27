import asyncio
import io
import requests
from pyrogram import Client
from libgen_api_enhanced import LibgenSearch, SearchTopic

BIN_CHANNEL_ID = -100123456789 # Put your Bookhubz Bin channel ID here!

# The genres or authors you want to scrape endlessly
BOOKS_TO_SCRAPE = [
    "Dostoevsky", "Psychological Thriller", "Classic Literature", "Manga"
]

async def background_book_scraper(app: Client, db):
    print("🤖 Background Library Builder Started...")
    s = LibgenSearch()
    
    while True: # Infinite loop to keep it running 24/7
        for query in BOOKS_TO_SCRAPE:
            try:
                # Search Fiction database first
                results = s.search_default(query, search_in=[SearchTopic.FICTION, SearchTopic.LIBGEN])
                if not results:
                    continue
                    
                for book in results[:3]: # Grab 3 books per cycle to avoid getting blocked
                    title = book.title
                    author = book.author
                    ext = book.extension
                    lang = book.language or "Unknown"
                    
                    # 1. Check if we already have it in MongoDB
                    exists = await db.books.find_one({"title": title.lower()})
                    if exists:
                        continue

                    # 2. Get the direct, ad-free download link
                    direct_link = s.resolved_download_link(book)
                    if not direct_link:
                        continue

                    # 3. Stream to RAM (Zero Disk Usage!)
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    response = requests.get(direct_link, stream=True, headers=headers, timeout=30)
                    if response.status_code != 200:
                        continue
                        
                    file_in_ram = io.BytesIO(response.content)
                    
                    # 4. Rename exactly how you want it
                    clean_title = title.replace("/", "-")
                    custom_file_name = f"{clean_title} by {author} [{lang}] @Bookhubz.{ext}"
                    file_in_ram.name = custom_file_name

                    # 5. Upload to Bin Channel
                    sent_msg = await app.send_document(
                        chat_id=BIN_CHANNEL_ID,
                        document=file_in_ram,
                        caption=f"📚 **{title}**\n👤 {author}\nAdded automatically to #Bookhubz"
                    )

                    # 6. Save to MongoDB
                    await db.books.insert_one({
                        "title": title.lower(),
                        "author": author.lower(),
                        "file_id": sent_msg.document.file_id,
                        "source": "auto_scraper"
                    })
                    print(f"✅ Added: {custom_file_name}")

                    # Sleep 2 minutes between downloads
                    await asyncio.sleep(120)

            except Exception as e:
                print(f"Scraper Error on '{query}': {e}")
                await asyncio.sleep(60) 
