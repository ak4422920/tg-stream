import os
import re
import uvicorn
from fastapi import FastAPI, Response
from telethon import TelegramClient
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

# 1. Credentials
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
CHANNEL_ID = os.getenv('CHANNEL_ID', 'me')

# --- Expanded Keyword List (Languages, Genres, Qualities) ---
KEYWORDS = {
    "Languages": ["Hindi", "English", "Tamil", "Telugu", "Malayalam", "Kannada", "Punjabi", "Bengali", "Marathi", "Korean", "Japanese", "Chinese", "Spanish", "French", "Dubbed", "Multi Audio", "Dual Audio"],
    "Genres": ["Action", "Comedy", "Horror", "Drama", "Sci-Fi", "Thriller", "Romance", "Documentary", "Anime", "Cartoon", "Series", "Marvel", "DC"],
    "Quality": ["480p", "720p", "1080p", "4K", "HDR", "BluRay", "WEB-DL", "CamRip"]
}

def clean_name(name):
    if not name: return "Unknown Movie"
    # Remove @username, t.me, links, and extra brackets
    name = re.sub(r'(@\w+|t\.me/\S+|https?://\S+|\[.*?\]|\{.*?\}|\(.*?\))', '', name)
    name = name.replace('_', ' ').replace('.', ' ')
    return name.strip()

def detect_tags(text):
    found = []
    all_keys = KEYWORDS["Languages"] + KEYWORDS["Genres"] + KEYWORDS["Quality"]
    for k in all_keys:
        if k.lower() in text.lower():
            found.append(k)
    return found if found else ["General"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 'None' used to avoid SQLite database lock issues on Koyeb
    await client.start(bot_token=BOT_TOKEN)
    print("✅ Universal OTT Store is Live!")
    yield
    await client.disconnect()

app = FastAPI(lifespan=lifespan)
client = TelegramClient(None, API_ID, API_HASH)

@app.get("/", response_class=HTMLResponse)
async def home(q: str = None, tag: str = None):
    movies_html = ""
    tag_cloud = set()
    
    async for message in client.iter_messages(CHANNEL_ID, limit=100):
        if message.video:
            raw_name = getattr(message.video.attributes[0], 'file_name', 'Movie')
            name = clean_name(raw_name)
            tags = detect_tags(name + " " + (message.text or ""))
            tag_cloud.update(tags)
            
            # Search & Filter Logic
            if q and q.lower() not in name.lower(): continue
            if tag and tag not in tags: continue
            
            size = round(message.video.size / (1024 * 1024), 2)
            movies_html += f"""
            <div style="background:#111; padding:20px; margin:15px 0; border-radius:15px; border:1px solid #222; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                <h3 style="margin:0 0 10px 0; color:#0f0;">🎬 {name}</h3>
                <p style="color:#aaa; font-size:13px; margin-bottom:15px;">
                    📏 <b>Size:</b> {size} MB | 🏷️ <b>Tags:</b> {", ".join(tags)}
                </p>
                <div style="display:flex; gap:10px;">
                    <a href="/watch/{message.id}" style="flex:1; background:#0f0; color:#000; padding:12px; text-decoration:none; border-radius:8px; font-weight:bold; text-align:center;">PLAY</a>
                    <a href="/stream/{message.id}" download="{raw_name}" style="flex:1; background:#222; color:#0f0; border:1px solid #0f0; padding:12px; text-decoration:none; border-radius:8px; font-weight:bold; text-align:center;">DOWNLOAD</a>
                </div>
            </div>
            """

    tag_btns = "".join([f'<a href="/?tag={t}" style="color:#0f0; text-decoration:none; margin:5px; border:1px solid #0f0; padding:6px 15px; border-radius:25px; display:inline-block; font-size:12px;">{t}</a>' for t in sorted(tag_cloud)])

    return f"""
    <html>
        <head><title>AK Universal Store</title></head>
        <body style="background:#000; color:#fff; font-family:sans-serif; padding:20px; max-width:900px; margin:auto;">
            <h1 style="text-align:center; color:#0f0; letter-spacing:2px;">🎥 AK MOVIE STORE</h1>
            
            <form action="/" style="text-align:center; margin-bottom:30px;">
                <input type="text" name="q" placeholder="Search movies, series..." style="padding:12px; border-radius:10px; width:70%; border:none; background:#111; color:#fff;">
                <button style="padding:12px 25px; background:#0f0; border-radius:10px; border:none; font-weight:bold; cursor:pointer; margin-left:10px;">Search</button>
            </form>

            <div style="text-align:center; margin-bottom:30px; border-bottom:1px solid #222; padding-bottom:20px;">
                <a href="/" style="color:#fff; margin-right:15px; text-decoration:none; font-weight:bold;">All</a> {tag_btns}
            </div>

            <div>{movies_html if movies_html else "<h3 style='text-align:center;color:#555;'>No movies found. Try another search!</h3>"}</div>
        </body>
    </html>
    """

@app.get("/watch/{{msg_id}}", response_class=HTMLResponse)
async def watch(msg_id: int):
    return f"""
    <body style="background:#000; color:#fff; text-align:center; padding-top:50px; font-family:sans-serif;">
        <h2 style="color:#0f0;">Streaming Mode</h2>
        <video width="95%" controls autoplay style="max-width:850px; border:2px solid #0f0; border-radius:15px; background:#000;">
            <source src="/stream/{{msg_id}}" type="video/mp4">
        </video><br><br>
        <a href="/" style="color:#0f0; text-decoration:none; font-size:18px;">← Back to Gallery</a>
    </body>
    """

@app.get("/stream/{{msg_id}}")
async def stream_video(msg_id: int):
    message = await client.get_messages(CHANNEL_ID, ids=msg_id)
    if message and message.video:
        async def gen():
            async for chunk in client.iter_download(message.video, chunk_size=1024*1024): yield chunk
        return Response(gen(), media_type="video/mp4")
    return {"error": "Video not found"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Keep workers=1 to prevent SQLite lock and memory issues
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=1)
