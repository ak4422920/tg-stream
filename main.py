import os, re, uvicorn, random
from fastapi import FastAPI, Response, Request
from telethon import TelegramClient
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

# 1. Configuration
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
CHANNEL_ID = os.getenv('CHANNEL_ID', '-1003617955958')
OWNER_USERNAME = os.getenv('OWNER_USERNAME', 'AK_ownerbot')

# ID Fix for Bots
if isinstance(CHANNEL_ID, str) and CHANNEL_ID.strip('-').isdigit():
    CHANNEL_ID = int(CHANNEL_ID)

movie_views = {}

KEYWORDS = {
    "Languages": ["Hindi", "English", "Tamil", "Telugu", "Malayalam", "Kannada", "Korean", "Japanese", "Dubbed", "Dual Audio"],
    "Genres": ["Action", "Comedy", "Horror", "Drama", "Sci-Fi", "Anime", "Series", "Marvel", "DC"],
    "Quality": ["480p", "720p", "1080p", "4K", "BluRay", "WEB-DL"]
}

def clean_name(name):
    if not name: return "Unknown Movie"
    name = re.sub(r'(@\w+|t\.me/\S+|https?://\S+|\[.*?\]|\{.*?\}|\(.*?\))', '', name)
    return name.replace('_', ' ').replace('.', ' ').strip()

def detect_tags(text):
    found = []
    all_keys = KEYWORDS["Languages"] + KEYWORDS["Genres"] + KEYWORDS["Quality"]
    for k in all_keys:
        if k.lower() in text.lower(): found.append(k)
    return found if found else ["General"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Using None session to prevent SQLite lock errors on Koyeb
    await client.start(bot_token=BOT_TOKEN)
    print("🚀 AK Premium OTT is Live!")
    yield
    await client.disconnect()

app = FastAPI(lifespan=lifespan)
client = TelegramClient(None, API_ID, API_HASH)

# Reusable Movie Card Function
def get_movie_card(msg_id, name, size, tags, views):
    return f"""
    <div style="background:#111; margin:10px; border-radius:12px; overflow:hidden; border:1px solid #222; width:250px; display:inline-block; vertical-align:top;">
        <img src="/thumb/{msg_id}" style="width:100%; height:140px; object-fit:cover; background:#222;">
        <div style="padding:12px; text-align:left;">
            <h3 style="margin:0; color:#0f0; font-size:14px; height:35px; overflow:hidden;">{name}</h3>
            <p style="color:#666; font-size:10px; margin:8px 0;">📏 {size} MB | 👁️ {views} Views</p>
            <a href="/watch/{msg_id}" style="display:block; background:#0f0; color:#000; padding:8px; text-decoration:none; border-radius:5px; font-weight:bold; text-align:center; font-size:12px; margin-bottom:5px;">PLAY</a>
            <a href="/stream/{msg_id}" download="{name}.mp4" style="display:block; background:#222; color:#0f0; border:1px solid #0f0; padding:6px; text-decoration:none; border-radius:5px; font-weight:bold; text-align:center; font-size:11px;">DOWNLOAD</a>
        </div>
    </div>
    """

@app.get("/", response_class=HTMLResponse)
async def home(q: str = None, tag: str = None):
    movies_html = ""
    tag_cloud = set()
    async for message in client.iter_messages(CHANNEL_ID, limit=50):
        if message.video:
            name = clean_name(getattr(message.video.attributes[0], 'file_name', 'Movie'))
            tags = detect_tags(name + " " + (message.text or ""))
            tag_cloud.update(tags)
            if q and q.lower() not in name.lower(): continue
            if tag and tag not in tags: continue
            size = round(message.video.size / (1024 * 1024), 2)
            movies_html += get_movie_card(message.id, name, size, tags, movie_views.get(message.id, 0))

    tag_btns = "".join([f'<a href="/?tag={t}" style="color:#0f0; text-decoration:none; margin:4px; border:1px solid #0f0; padding:4px 10px; border-radius:20px; display:inline-block; font-size:11px;">{t}</a>' for t in sorted(tag_cloud)])

    return f"""
    <html>
        <body style="background:#000; color:#fff; font-family:sans-serif; padding:20px; text-align:center;">
            <div style="display:flex; justify-content:space-between; align-items:center; max-width:1000px; margin:auto;">
                <h1 style="color:#0f0;">🎥 AK PREMIUM</h1>
                <a href="https://t.me/{OWNER_USERNAME}" style="background:#0088cc; color:#fff; padding:8px 15px; text-decoration:none; border-radius:8px; font-size:13px; font-weight:bold;">➕ REQUEST</a>
            </div>
            <form action="/" style="margin:20px 0;"><input type="text" name="q" placeholder="Search movies..." style="padding:10px; border-radius:8px; width:60%; border:none; background:#111; color:#fff;"> <button style="padding:10px 20px; background:#0f0; border:none; border-radius:8px; cursor:pointer;">Find</button></form>
            <div style="margin-bottom:20px;">{tag_btns}</div>
            <div style="display:flex; flex-wrap:wrap; justify-content:center;">{movies_html if movies_html else "No Results Found"}</div>
        </body>
    </html>
    """

@app.get("/watch/{{msg_id}}", response_class=HTMLResponse)
async def watch(msg_id: int):
    movie_views[msg_id] = movie_views.get(msg_id, 0) + 1
    related_html = ""
    # Fetch 4 random related movies
    async for msg in client.iter_messages(CHANNEL_ID, limit=20):
        if msg.video and msg.id != msg_id:
            name = clean_name(getattr(msg.video.attributes[0], 'file_name', 'Movie'))
            size = round(msg.video.size / (1024 * 1024), 2)
            related_html += get_movie_card(msg.id, name, size, [], movie_views.get(msg.id, 0))
            if related_html.count('background:#111') >= 4: break

    return f"""
    <body style="background:#000; color:#fff; text-align:center; padding:20px; font-family:sans-serif;">
        <video width="100%" controls autoplay style="max-width:900px; border:2px solid #0f0; border-radius:15px; background:#000;">
            <source src="/stream/{{msg_id}}" type="video/mp4">
        </video>
        <div style="margin:20px 0;"><a href="/" style="color:#0f0; text-decoration:none; font-size:18px;">← Back to Home</a></div>
        <hr style="border:1px solid #222; margin:40px 0;">
        <h2 style="color:#0f0;">🔥 YOU MAY ALSO LIKE</h2>
        <div style="display:flex; flex-wrap:wrap; justify-content:center;">{related_html}</div>
    </body>
    """

@app.get("/thumb/{{msg_id}}")
async def get_thumb(msg_id: int):
    message = await client.get_messages(CHANNEL_ID, ids=msg_id)
    if message and message.video and message.video.thumbs:
        thumb_data = await client.download_media(message.video.thumbs[-1], file=bytes)
        return Response(content=thumb_data, media_type="image/jpeg")
    return Response(status_code=404)

@app.get("/stream/{{msg_id}}")
async def stream_video(msg_id: int):
    message = await client.get_messages(CHANNEL_ID, ids=msg_id)
    if message and message.video:
        async def gen():
            async for chunk in client.iter_download(message.video, chunk_size=1024*1024): yield chunk
        return Response(gen(), media_type="video/mp4")
    return {"error": "Not found"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=1)
