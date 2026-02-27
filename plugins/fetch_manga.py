import io
import requests
from PIL import Image
from pyrogram import Client, filters
from database.ia_filterdb import save_file, Media 

BIN_CHANNEL_ID = -1003793921200 # Your Bookhubz Bin channel ID

# Wrapper to make the file compatible with your native database logic
class MockMedia:
    def __init__(self, document, message):
        self.file_id = document.file_id
        self.file_name = document.file_name
        self.file_size = document.file_size
        self.file_type = "document"
        self.mime_type = document.mime_type
        self.caption = message.caption

@Client.on_message(filters.command("manga"))
async def fetch_manga_on_demand(client, message):
    # Check if they provided a title and chapter
    if len(message.command) < 3:
        return await message.reply_text(
            "⚠️ Please provide a Manga Title AND Chapter Number.\n\n"
            "**Example:** `/manga Jujutsu Kaisen 1`"
        )
        
    # Extract title and chapter number
    args = message.text.split(" ", 1)[1]
    try:
        parts = args.rsplit(" ", 1)
        title = parts[0]
        chapter_num = parts[1]
    except IndexError:
        return await message.reply_text("⚠️ Please specify the chapter number at the end.\nExample: `/manga Lookism 10`")

    status_msg = await message.reply_text(f"🔍 Searching MangaDex for **{title}** (Chapter {chapter_num})...")
    
    try:
        # 1. Search MangaDex for the Manga ID
        search_url = f"https://api.mangadex.org/manga?title={title}&limit=1&availableTranslatedLanguage[]=en"
        res = requests.get(search_url).json()
        if not res.get("data"):
            return await status_msg.edit_text("❌ Couldn't find that manga on MangaDex. Check your spelling!")
        
        manga_id = res["data"][0]["id"]
        # Try to get the English title, fallback to original if not found
        manga_title = res["data"][0]["attributes"]["title"].get("en") or list(res["data"][0]["attributes"]["title"].values())[0]

        # 2. Get the Chapter ID
        feed_url = f"https://api.mangadex.org/manga/{manga_id}/feed?translatedLanguage[]=en&chapter={chapter_num}&limit=1"
        feed_res = requests.get(feed_url).json()
        if not feed_res.get("data"):
            return await status_msg.edit_text(f"❌ Couldn't find **Chapter {chapter_num}** for **{manga_title}** in English.")
        
        chapter_id = feed_res["data"][0]["id"]

        # 3. Get the Image Server Links
        server_url = f"https://api.mangadex.org/at-home/server/{chapter_id}"
        server_res = requests.get(server_url).json()
        base_url = server_res["baseUrl"]
        chapter_hash = server_res["chapter"]["hash"]
        pages = server_res["chapter"]["data"]

        clean_title = manga_title.replace("/", "-").replace(":", "")
        custom_file_name = f"{clean_title} Chapter {chapter_num} [English] @Bookhubz.pdf"

        # 4. Check DB before doing the heavy lifting
        exists = await Media.count_documents({"file_name": custom_file_name}, limit=1)
        if exists:
            return await status_msg.edit_text(f"✅ **{clean_title} Chapter {chapter_num}** is already in our database!\n\nJust search for it normally.")

        await status_msg.edit_text(f"📥 Found Chapter {chapter_num}!\nDownloading {len(pages)} pages to server buffer...")

        # 5. Download and Compile Images into a PDF
        images = []
        for i, page in enumerate(pages):
            img_url = f"{base_url}/data/{chapter_hash}/{page}"
            img_res = requests.get(img_url)
            if img_res.status_code == 200:
                img = Image.open(io.BytesIO(img_res.content)).convert("RGB")
                images.append(img)
        
        if not images:
            return await status_msg.edit_text("❌ Failed to download the chapter images from MangaDex servers.")

        await status_msg.edit_text("📚 Stitching pages into a high-quality PDF...")
        
        pdf_bytes = io.BytesIO()
        images[0].save(
            pdf_bytes, 
            format="PDF", 
            save_all=True, 
            append_images=images[1:]
        )
        pdf_bytes.name = custom_file_name
        pdf_bytes.seek(0) # Reset buffer position

        await status_msg.edit_text("📤 Uploading compiled Manga to Bookhubz Library...")

        # 6. Upload to Bin Channel
        sent_msg = await client.send_document(
            chat_id=BIN_CHANNEL_ID,
            document=pdf_bytes,
            caption=f"📚 **{clean_title}**\n📖 Chapter {chapter_num}\n🌐 Language: English\n\nGenerated & Added on-demand to #Bookhubz"
        )

        # 7. Save to DB
        media_obj = MockMedia(sent_msg.document, sent_msg)
        saved, status = await save_file(media_obj)
        
        if saved:
            await status_msg.edit_text(f"🎉 **Success!**\n\n**{clean_title} Chapter {chapter_num}** has been added!\n\nType the name normally to get your file!")
        else:
            await status_msg.edit_text("⚠️ Sent to channel, but there was a minor issue indexing it to the database.")

    except Exception as e:
        await status_msg.edit_text(f"❌ An error occurred: `{str(e)}`")
