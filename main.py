import os, re, uvicorn, time, random
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

try:
    CHANNEL_ID = int(str(CHANNEL_ID).strip())
except:
    pass

# --- GENRE LIST (Yahan se category pakdi jayegi) ---
GENRE_KEYWORDS = {
    "Action": ["action", "thriller", "fight", "war"],
    "Horror": ["horror", "scary", "ghost", "evil"],
    "Comedy": ["comedy", "funny", "laugh", "drama"],
    "Sci-Fi": ["sci-fi", "science", "space", "future"],
    "Anime": ["anime", "naruto", "hindi dubbed"],
    "Adult": ["18+", "uncut", "hot"]
}

CACHE = {"data": [], "last_update": 0}
CACHE_TIME = 600 

# --- AUTO GENRE LOGIC ---
def get_genres(name):
    found = []
    for genre, keys in GENRE_KEYWORDS.items():
        for key in keys:
            if key.lower() in name.lower():
                found.append(genre)
                break
    return found if found else ["General"]

def clean_name(name):
    if not name: return "Unknown Movie"
    name = re.sub(r'(S\d+|E\d+|Season\s*\d+|Episode\s*\d+|Part\s*\d+)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'(@\w+|t\.me/\S+|https?://\S+|\[.*?\]|\{.*?\}|\(.*?\))', '', name)
    return name.replace('_', ' ').replace('.', ' ').strip()

def is_series(name):
    return bool(re.search(r'(S\d+|E\d+|Season|Episode|Part)', name, re.IGNORECASE))

@asynccontextmanager
async def lifespan(app: FastAPI):
    await client.start(bot_token=BOT_TOKEN)
    try:
        # Pre-fetch entity to avoid history access errors
        await client.get_entity(CHANNEL_ID)
    except: pass
    yield
    await client.disconnect()

app = FastAPI(lifespan=lifespan)
client = TelegramClient(None, API_ID, API_HASH)

async def update_cache():
    if time.time() - CACHE["last_update"] > CACHE_TIME:
        new_list = []
        try:
            # Bot privacy settings check in BotFather
            async for message in client.iter_messages(CHANNEL_ID, limit=500):
                if message.video:
                    raw = getattr(message.video.attributes[0], 'file_name', 'Video')
                    new_list.append({
                        "id": message.id,
                        "raw_name": raw,
                        "c_name": clean_name(raw),
                        "is_ser": is_series(raw),
                        "genres": get_genres(raw),
                        "size": round(message.video.size/(1024*1024), 2)
                    })
            CACHE["data"] = new_list
            CACHE["last_update"] = time.time()
        except: pass

@app.get("/", response_class=HTMLResponse)
async def home(q: str = None, page: int = 1):
    await update_cache()
    data = CACHE["data"]
    if q: data = [i for i in data if q.lower() in i["c_name"].lower()]
    
    grouped = {}
    for item in data:
        name = item["c_name"]
        if name not in grouped: grouped[name] = item
    
    final_list = list(grouped.values())
    paginated = final_list[(page-1)*20 : page*20]

    cards_html = ""
    for itm in paginated:
        label = "SERIES" if itm["is_ser"] else "MOVIE"
        # Displaying Genre Tags
        genre_tags = "".join([f'<span style="background:#333; color:#0f0; padding:2px 5px; border-radius:4px; font-size:9px; margin-right:4px;">{g}</span>' for g in itm["genres"]])
        
        url = f"/series/{itm['c_name']}" if itm["is_ser"] else f"/watch/{itm['id']}"
        cards_html += f"""
        <div style="background:#111; margin:12px; border-radius:15px; border:1px solid #222; width:250px; display:inline-block; vertical-align:top; transition: 0.3s;">
            <div style="position:relative;">
                <img src="/thumb/{itm['id']}" style="width:100%; height:150px; object-fit:cover; border-radius:15px 15px 0 0;">
                <span style="position:absolute; top:10px; left:10px; background:#0f0; color:#000; padding:3px 8px; border-radius:5px; font-size:10px; font-weight:bold;">{label}</span>
            </div>
            <div style="padding:15px; text-align:left;">
                <div style="margin-bottom:8px;">{genre_tags}</div>
                <h3 style="margin:0; color:#fff; font-size:14px; height:40px; overflow:hidden;">{itm['c_name']}</h3>
                <p style="color:#666; font-size:10px;">Size: {itm['size']} MB</p>
                <a href="{url}" style="display:block; background:#0f0; color:#000; padding:10px; text-decoration:none; border-radius:8px; font-weight:bold; text-align:center; margin-top:10px;">VIEW</a>
            </div>
        </div>
        """

    return f"""
    <html><body style="background:#000; color:#fff; font-family:sans-serif; text-align:center; padding:20px;">
        <h1 style="color:#0f0;">🎥 AK PREMIUM</h1>
        <form><input name="q" placeholder="Search..." style="padding:12px; width:65%; border-radius:10px; background:#111; color:#fff; border:none;"></form>
        <div style="display:flex; flex-wrap:wrap; justify-content:center;">{cards_html if cards_html else "No Content. Bot permissions check karein!"}</div>
    </body></html>
    """

# (Baaki routes like watch, stream, thumb will be same as previous code)
@app.get("/watch/{msg_id}", response_class=HTMLResponse)
async def watch(request: Request, msg_id: int):
    base_url = str(request.base_url).rstrip('/')
    vlc_url = f"vlc://{base_url}/stream/{msg_id}"
    return f"""<body style="background:#000; color:#fff; text-align:center; padding:20px;"><video width="100%" controls autoplay style="max-width:900px; border:2px solid #0f0; border-radius:15px;"><source src="/stream/{msg_id}" type="video/mp4"></video><div style="margin:25px;"><a href="{vlc_url}" style="background:#f80; color:#fff; padding:12px 25px; text-decoration:none; border-radius:10px; font-weight:bold;">OPEN IN VLC</a></div><a href="/" style="color:#0f0;">← Home</a></body>"""

@app.get("/thumb/{msg_id}")
async def get_thumb(msg_id: int):
    m = await client.get_messages(CHANNEL_ID, ids=msg_id)
    if m and m.video and m.video.thumbs:
        t = await client.download_media(m.video.thumbs[-1], file=bytes)
        return Response(content=t, media_type="image/jpeg")
    return Response(status_code=404)

@app.get("/stream/{msg_id}")
async def stream_video(msg_id: int):
    m = await client.get_messages(CHANNEL_ID, ids=msg_id)
    if m and m.video:
        async def gen():
            async for chunk in client.iter_download(m.video, chunk_size=1024*1024): yield chunk
        return Response(gen(), media_type="video/mp4")
    return {"error": "Not found"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), workers=1)
