from aiohttp import web
import re
import math
import logging
import secrets
import time
import mimetypes
from aiohttp.http_exceptions import BadStatusLine
from dreamxbotz.Bot import multi_clients, work_loads, dreamxbotz
from dreamxbotz.server.exceptions import FIleNotFound, InvalidHash
from dreamxbotz.zzint import StartTime, __version__
from dreamxbotz.util.custom_dl import ByteStreamer
from dreamxbotz.util.time_format import get_readable_time
from dreamxbotz.util.render_template import render_page
from info import *


routes = web.RouteTableDef()

@routes.get("/favicon.ico")
async def favicon_route_handler(request):
    return web.FileResponse('dreamxbotz/template/favicon.ico')

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response("dreamxbotz")

@routes.get(r"/watch/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
        return web.Response(text=await render_page(id, secure_hash), content_type='text/html')
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

@routes.get(r"/{path:\S+}", allow_head=True)
async def stream_handler(request: web.Request):
    try:
        path = request.match_info["path"]
        match = re.search(r"^([a-zA-Z0-9_-]{6})(\d+)$", path)
        if match:
            secure_hash = match.group(1)
            id = int(match.group(2))
        else:
            id = int(re.search(r"(\d+)(?:\/\S+)?", path).group(1))
            secure_hash = request.rel_url.query.get("hash")
        return await media_streamer(request, id, secure_hash)
    except InvalidHash as e:
        raise web.HTTPForbidden(text=e.message)
    except FIleNotFound as e:
        raise web.HTTPNotFound(text=e.message)
    except (AttributeError, BadStatusLine, ConnectionResetError):
        pass
    except Exception as e:
        logging.critical(e.with_traceback(None))
        raise web.HTTPInternalServerError(text=str(e))

class_cache = {}

async def media_streamer(request: web.Request, id: int, secure_hash: str):
    range_header = request.headers.get("Range", 0)
    
    index = min(work_loads, key=work_loads.get)
    faster_client = multi_clients[index]
    
    if MULTI_CLIENT:
        logging.info(f"Client {index} is now serving {request.remote}")

    if faster_client in class_cache:
        tg_connect = class_cache[faster_client]
        logging.debug(f"Using cached ByteStreamer object for client {index}")
    else:
        logging.debug(f"Creating new ByteStreamer object for client {index}")
        tg_connect = ByteStreamer(faster_client)
        class_cache[faster_client] = tg_connect
    logging.debug("before calling get_file_properties")
    file_id = await tg_connect.get_file_properties(id)
    logging.debug("after calling get_file_properties")
    
    if file_id.unique_id[:6] != secure_hash:
        logging.debug(f"Invalid hash for message with ID {id}")
        raise InvalidHash
    
    file_size = file_id.file_size

    if range_header:
        from_bytes, until_bytes = range_header.replace("bytes=", "").split("-")
        from_bytes = int(from_bytes)
        until_bytes = int(until_bytes) if until_bytes else file_size - 1
    else:
        from_bytes = request.http_range.start or 0
        until_bytes = (request.http_range.stop or file_size) - 1

    if (until_bytes > file_size) or (from_bytes < 0) or (until_bytes < from_bytes):
        return web.Response(
            status=416,
            body="416: Range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    chunk_size = 1024 * 1024
    until_bytes = min(until_bytes, file_size - 1)

    offset = from_bytes - (from_bytes % chunk_size)
    first_part_cut = from_bytes - offset
    last_part_cut = until_bytes % chunk_size + 1

    req_length = until_bytes - from_bytes + 1
    part_count = math.ceil(until_bytes / chunk_size) - math.floor(offset / chunk_size)
    body = tg_connect.yield_file(
        file_id, index, offset, first_part_cut, last_part_cut, part_count, chunk_size
    )

    mime_type = file_id.mime_type
    file_name = file_id.file_name
    disposition = "attachment"

    if mime_type:
        if not file_name:
            try:
                file_name = f"{secrets.token_hex(2)}.{mime_type.split('/')[1]}"
            except (IndexError, AttributeError):
                file_name = f"{secrets.token_hex(2)}.unknown"
    else:
        if file_name:
            mime_type = mimetypes.guess_type(file_id.file_name)
        else:
            mime_type = "application/octet-stream"
            file_name = f"{secrets.token_hex(2)}.unknown"

    return web.Response(
        status=206 if range_header else 200,
        body=body,
        headers={
            "Content-Type": f"{mime_type}",
            "Content-Range": f"bytes {from_bytes}-{until_bytes}/{file_size}",
            "Content-Length": str(req_length),
            "Content-Disposition": f'{disposition}; filename="{file_name}"',
            "Accept-Ranges": "bytes",
        },
    )


# ─────────────────────────────────────────────
# 🌐 GOOGLE BOOKS API & MINI APP SEARCH ROUTE 🌐
# ─────────────────────────────────────────────
import aiohttp
import os
import asyncio
import re

async def fetch_book_metadata(title: str):
    default = {"cover": "", "authors": "Unknown Author", "synopsis": "", "buy_link": ""}
    query = f"intitle:{title}"
    params = {"q": query, "maxResults": 1, "printType": "books", "fields": "items(volumeInfo(title,authors,description,imageLinks,canonicalVolumeLink,infoLink))"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.googleapis.com/books/v1/volumes", params=params, timeout=6) as resp:
                if resp.status != 200: return default
                data = await resp.json()
                items = data.get("items")
                if not items: return default
                info = items[0].get("volumeInfo", {})
                image_links = info.get("imageLinks", {})
                cover = (image_links.get("thumbnail") or image_links.get("smallThumbnail") or "").replace("http://", "https://")
                authors = info.get("authors") or []
                synopsis = info.get("description", "")
                if len(synopsis) > 500: synopsis = synopsis[:497].rstrip() + "…"
                return {
                    "cover": cover,
                    "authors": ", ".join(authors) if authors else default["authors"],
                    "synopsis": synopsis,
                    "buy_link": info.get("infoLink") or "",
                }
    except:
        return default

# CORS Preflight
@routes.options("/api/search")
async def search_options(request: web.Request):
    return web.Response(headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"})

# The Main Search API
@routes.get("/api/search")
async def search_handler(request: web.Request):
    # ---> THE FIX: Import moved inside the function to prevent Circular Import Crash <---
    from database.ia_filterdb import Media
    
    headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS", "Access-Control-Allow-Headers": "Content-Type"}
    query = request.rel_url.query.get("q", "").strip()
    
    if not query or len(query) < 2:
        return web.json_response({"results": [], "total": 0}, headers=headers)
        
    regex = {"$regex": re.escape(query), "$options": "i"}
    cursor = Media.collection.find({"file_name": regex}).limit(15)
    docs = await cursor.to_list(length=15)
    
    if not docs:
        return web.json_response({"results": [], "total": 0}, headers=headers)
        
    async def enrich(doc):
        file_name = doc.get("file_name", "")
        # Clean filename to get a good book title search
        clean_title = re.sub(r"\[.*?\]|\(.*?\)|(?:1080p|720p|480p|pdf|epub|mobi|cbz|cbr)", "", file_name, flags=re.IGNORECASE).replace(".", " ").replace("_", " ").strip()
        if not clean_title: clean_title = query
        
        meta = await fetch_book_metadata(clean_title)
        
        # Affiliate link (fallback to your mikasa tag)
        amazon_query = clean_title.replace(" ", "+")
        AMAZON_TAG = os.environ.get("AMAZON_TAG", "mikasabooks-21")
        amazon_link = meta.get("buy_link") or f"https://www.amazon.in/s?k={amazon_query}&tag={AMAZON_TAG}"
        
        return {
            "file_id": doc.get("file_id", ""),
            "title": clean_title[:45] + ("..." if len(clean_title)>45 else ""),
            "author": meta["authors"],
            "synopsis": meta["synopsis"],
            "cover": meta["cover"],
            "buy_link": amazon_link,
            "file_size": doc.get("file_size"),
        }
        
    enriched = await asyncio.gather(*[enrich(doc) for doc in docs])
    return web.json_response({"results": list(enriched), "total": len(enriched)}, headers=headers)
