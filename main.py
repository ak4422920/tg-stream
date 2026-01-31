import os, re, uvicorn, time
from fastapi import FastAPI, Response, Request
from telethon import TelegramClient, events
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient

# 1. Configuration (Koyeb Env Vars)
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
CHANNEL_ID = int(os.getenv('CHANNEL_ID', '-1003617955958'))
MONGO_URI = os.getenv('MONGO_URI', '') # MongoDB Atlas ka link yahan dalo
OWNER_USERNAME = os.getenv('OWNER_USERNAME', 'AK_ownerbot')

# Database Setup
db_client = AsyncIOMotorClient(MONGO_URI)
db = db_client['AK_OTT_DATABASE']
movies_col = db['all_movies']

# Telethon Client
client = TelegramClient(None, API_ID, API_HASH)

# --- Helper Logic ---
def clean_name(name):
    if not name: return "Unknown File"
    # Series grouping ke liye cleaning
    name = re.sub(r'(S\d+|E\d+|Season\s*\d+|Episode\s*\d+|Part\s*\d+)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'(@\w+|t\.me/\S+|https?://\S+|\[.*?\]|\{.*?\}|\(.*?\))', '', name)
    return name.replace('_', ' ').replace('.', ' ').strip()

def is_series(name):
    return bool(re.search(r'(S\d+|E\d+|Season|Episode|Part)', name, re.IGNORECASE))

# --- LIVE LISTENER: Nayi movie aate hi DB mein save karega ---
@client.on(events.NewMessage(chats=CHANNEL_ID))
async def save_to_db(event):
    if event.message.video:
        raw_fn = getattr(event.message.video.attributes[0], 'file_name', 'Video')
        # Database mein detail store karna taaki history read na karni pade
        movie_data = {
            "msg_id": event.message.id,
            "raw_name": raw_fn,
            "clean_name": clean_name(raw_fn),
            "is_series": is_series(raw_fn),
            "file_size": round(event.message.video.size / (1024 * 1024), 2),
            "timestamp": time.time()
        }
        await movies_col.update_one({"msg_id": event.message.id}, {"$set": movie_data}, upsert=True)
        print(f"✅ Indexed: {raw_fn}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start bot and connect to Telegram
    await client.start(bot_token=BOT_TOKEN)
    print("🚀 AK PREMIUM OTT with MongoDB is LIVE!")
    yield
    await client.disconnect()

app = FastAPI(lifespan=lifespan)

# --- WEB UI ROUTES ---
@app.get("/", response_class=HTMLResponse)
async def home(q: str = None, page: int = 1):
    # Live fetch ki jagah Database se data uthana
    query = {}
    if q:
        query = {"clean_name": {"$regex": q, "$options": "i"}}
    
    # Latest movies pehle dikhengi
    cursor = movies_col.find(query).sort("timestamp", -1)
    all_data = await cursor.to_list(length=1000)
    
    # Series grouping logic
    grouped = {}
    for itm in all_data:
        name = itm["clean_name"]
        if name not in grouped: grouped[name] = itm
    
    final_list = list(grouped.values())
    paginated = final_list[(page-1)*20 : page*20]

    cards_html = ""
    for itm in paginated:
        label = "SERIES" if itm["is_series"] else "MOVIE"
        url = f"/series/{itm['clean_name']}" if itm["is_series"] else f"/watch/{itm['msg_id']}"
        cards_html += f"""
        <div style="background:#111; margin:12px; border-radius:15px; border:1px solid #222; width:250px; display:inline-block; vertical-align:top; padding:10px;">
            <div style="position:relative;">
                <img src="/thumb/{itm['msg_id']}" style="width:100%; height:145px; border-radius:12px; object-fit:cover; background:#222;">
                <span style="position:absolute; top:8px; left:8px; background:#0f0; color:#000; padding:2px 8px; border-radius:5px; font-size:10px; font-weight:bold;">{label}</span>
            </div>
            <div style="padding:10px; text-align:left;">
                <h3 style="margin:0; color:#fff; font-size:14px; height:40px; overflow:hidden;">{itm['clean_name']}</h3>
                <p style="color:#666; font-size:10px;">Size: {itm['file_size']} MB</p>
                <a href="{url}" style="display:block; background:#0f0; color:#000; padding:10px; text-decoration:none; border-radius:8px; font-weight:bold; text-align:center; margin-top:5px;">VIEW</a>
            </div>
        </div>
        """

    return f"""
    <html><body style="background:#000; color:#fff; font-family:sans-serif; text-align:center; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; max-width:1000px; margin:auto;">
            <h1 style="color:#0f0;">🎥 AK PREMIUM</h1>
            <a href="https://t.me/{OWNER_USERNAME}" style="background:#0088cc; color:#fff; padding:10px 20px; text-decoration:none; border-radius:10px; font-weight:bold; font-size:12px;">➕ REQUEST</a>
        </div>
        <form style="margin:20px;"><input name="q" placeholder="Search..." style="padding:12px; width:65%; border-radius:10px; background:#111; color:#fff; border:none;"></form>
        <div style="display:flex; flex-wrap:wrap; justify-content:center;">{cards_html if cards_html else "No Movies Found. Channel mein movies forward karein!"}</div>
    </body></html>
    """

@app.get("/series/{series_name}", response_class=HTMLResponse)
async def list_episodes(series_name: str):
    cursor = movies_col.find({"clean_name": series_name}).sort("timestamp", 1)
    eps_list = await cursor.to_list(length=100)
    eps_html = "".join([f'<div style="background:#111; padding:15px; margin:10px; border-radius:10px; border:1px solid #222; display:flex; justify-content:space-between;"><span>{i["raw_name"]}</span><a href="/watch/{i["msg_id"]}" style="color:#0f0; text-decoration:none; font-weight:bold;">PLAY</a></div>' for i in eps_list])
    return f"<html><body style='background:#000; color:#fff; font-family:sans-serif; padding:20px;'><h1>📺 {series_name}</h1><div style='max-width:800px; margin:auto;'>{eps_html}</div><br><a href='/' style='color:#0f0;'>← Back Home</a></body></html>"

@app.get("/watch/{msg_id}", response_class=HTMLResponse)
async def watch(request: Request, msg_id: int):
    base_url = str(request.base_url).rstrip('/')
    stream_url = f"{base_url}/stream/{msg_id}"
    vlc_url = f"vlc://{stream_url}"
    return f"""
    <body style="background:#000; color:#fff; text-align:center; padding:20px; font-family:sans-serif;">
        <video width="100%" controls autoplay style="max-width:850px; border:2px solid #0f0; border-radius:15px;"><source src="/stream/{msg_id}" type="video/mp4"></video>
        <div style="margin:25px; display:flex; justify-content:center; gap:15px;">
            <a href="{vlc_url}" style="background:#f80; color:#fff; padding:12px 25px; text-decoration:none; border-radius:10px; font-weight:bold;">VLC PLAYER</a>
            <a href="/stream/{msg_id}" download style="background:#333; color:#fff; padding:12px 25px; text-decoration:none; border-radius:10px;">DOWNLOAD 📥</a>
        </div>
        <a href="/" style="color:#0f0; text-decoration:none;">← Back Home</a>
    </body>
    """

# --- Telegram Proxies (Streaming/Thumb) ---
@app.get("/stream/{msg_id}")
async def stream_video(msg_id: int):
    m = await client.get_messages(CHANNEL_ID, ids=msg_id)
    if m and m.video:
        async def gen():
            async for chunk in client.iter_download(m.video, chunk_size=1024*1024): yield chunk
        return Response(gen(), media_type="video/mp4")
    return {"error": "Video not found"}

@app.get("/thumb/{msg_id}")
async def get_thumb(msg_id: int):
    m = await client.get_messages(CHANNEL_ID, ids=msg_id)
    if m and m.video and m.video.thumbs:
        t = await client.download_media(m.video.thumbs[-1], file=bytes)
        return Response(t, media_type="image/jpeg")
    return Response(status_code=404)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), workers=1)
