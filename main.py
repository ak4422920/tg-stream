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

# ID Fix for stability
try:
    CHANNEL_ID = int(str(CHANNEL_ID).strip())
except:
    pass

movie_views = {}

def clean_name(name):
    if not name: return "Unknown"
    # Series patterns remove karna grouping ke liye
    name = re.sub(r'(S\d+|E\d+|Season\s*\d+|Episode\s*\d+|Part\s*\d+)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'(@\w+|t\.me/\S+|https?://\S+|\[.*?\]|\{.*?\}|\(.*?\))', '', name)
    return name.replace('_', ' ').replace('.', ' ').strip()

def is_series(name):
    return bool(re.search(r'(S\d+|E\d+|Season|Episode|Part)', name, re.IGNORECASE))

@asynccontextmanager
async def lifespan(app: FastAPI):
    await client.start(bot_token=BOT_TOKEN)
    try:
        # Cache channel entity to prevent GetHistory errors
        await client.get_entity(CHANNEL_ID)
        print("✅ Entity Cached Successfully")
    except Exception as e:
        print(f"⚠️ Entity Warning: {e}")
    print("🚀 AK Premium OTT is Live!")
    yield
    await client.disconnect()

app = FastAPI(lifespan=lifespan)
client = TelegramClient(None, API_ID, API_HASH)

# --- UI Components ---
def get_card(msg_id, name, is_ser, count, size):
    label = "SERIES" if is_ser else "MOVIE"
    btn = "VIEW EPISODES" if is_ser else "PLAY NOW"
    url = f"/series/{name}" if is_ser else f"/watch/{msg_id}"
    views = movie_views.get(msg_id, random.randint(100, 500))
    
    return f"""
    <div style="background:#111; margin:10px; border-radius:15px; overflow:hidden; border:1px solid #222; width:260px; display:inline-block; vertical-align:top; transition:0.3s;">
        <div style="position:relative;">
            <img src="/thumb/{msg_id}" style="width:100%; height:150px; object-fit:cover; background:#222;">
            <span style="position:absolute; top:10px; left:10px; background:#0f0; color:#000; padding:2px 8px; border-radius:5px; font-size:10px; font-weight:bold;">{label}</span>
        </div>
        <div style="padding:15px; text-align:left;">
            <h3 style="margin:0; color:#fff; font-size:14px; height:35px; overflow:hidden;">{name}</h3>
            <p style="color:#666; font-size:11px; margin:10px 0;">📏 {size} MB | 👁️ {views} Views</p>
            <a href="{url}" style="display:block; background:#0f0; color:#000; padding:10px; text-decoration:none; border-radius:8px; font-weight:bold; text-align:center; font-size:12px;">{btn}</a>
        </div>
    </div>
    """

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def home(q: str = None):
    items = {}
    try:
        async for message in client.iter_messages(CHANNEL_ID, limit=100):
            if message.video:
                raw_name = getattr(message.video.attributes[0], 'file_name', 'Video')
                c_name = clean_name(raw_name)
                if q and q.lower() not in c_name.lower(): continue
                if c_name not in items:
                    items[c_name] = {"id": message.id, "ser": is_series(raw_name), "sz": round(message.video.size/(1024*1024), 2)}
    except Exception as e:
        return f"<h1>Error: {e}</h1>"

    cards = "".join([get_card(v["id"], k, v["ser"], 0, v["sz"]) for k, v in items.items()])
    
    return f"""
    <html><body style="background:#000; color:#fff; font-family:sans-serif; text-align:center; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; max-width:1000px; margin:auto;">
            <h1 style="color:#0f0;">🎥 AK PREMIUM</h1>
            <a href="https://t.me/{OWNER_USERNAME}" style="background:#0088cc; color:#fff; padding:10px 20px; text-decoration:none; border-radius:10px; font-weight:bold; font-size:14px;">➕ REQUEST</a>
        </div>
        <form style="margin:25px;"><input name="q" placeholder="Search..." style="padding:12px; width:60%; border-radius:10px; border:none; background:#111; color:#fff;"> <button style="padding:12px 20px; background:#0f0; border-radius:10px; font-weight:bold; cursor:pointer;">Find</button></form>
        <div style="display:flex; flex-wrap:wrap; justify-content:center;">{cards if cards else "No Content"}</div>
    </body></html>
    """

@app.get("/series/{series_name}", response_class=HTMLResponse)
async def list_episodes(series_name: str):
    eps = ""
    async for msg in client.iter_messages(CHANNEL_ID, limit=100):
        if msg.video and clean_name(getattr(msg.video.attributes[0], 'file_name', '')) == series_name:
            eps += f"""
            <div style="background:#111; padding:15px; margin:10px; border-radius:10px; border:1px solid #333; display:flex; justify-content:space-between; align-items:center;">
                <h4 style="margin:0; color:#0f0;">{getattr(msg.video.attributes[0], 'file_name', 'Video')}</h4>
                <a href="/watch/{msg.id}" style="background:#0f0; color:#000; padding:8px 15px; text-decoration:none; border-radius:5px; font-weight:bold;">PLAY</a>
            </div>"""
    return f"<html><body style='background:#000; color:#fff; font-family:sans-serif; padding:20px;'><h1>📺 {series_name}</h1>{eps}<br><a href='/' style='color:#0f0;'>← Back Home</a></body></html>"

@app.get("/watch/{msg_id}", response_class=HTMLResponse)
async def watch(msg_id: int):
    movie_views[msg_id] = movie_views.get(msg_id, 0) + 1
    related = ""
    async for m in client.iter_messages(CHANNEL_ID, limit=10):
        if m.video and m.id != msg_id:
            n = clean_name(getattr(m.video.attributes[0], 'file_name', 'Movie'))
            related += f'<a href="/watch/{m.id}" style="color:#0f0; display:block; margin:5px; text-decoration:none;">🎬 {n}</a>'
    
    return f"""
    <body style="background:#000; color:#fff; text-align:center; padding-top:40px; font-family:sans-serif;">
        <video width="95%" controls autoplay style="max-width:850px; border:2px solid #0f0; border-radius:15px; background:#000;">
            <source src="/stream/{msg_id}" type="video/mp4">
        </video>
        <div style="margin:20px;">
            <a href="/" style="color:#0f0; text-decoration:none; font-size:18px;">← Home</a> | 
            <a href="/stream/{msg_id}" download style="color:#aaa; text-decoration:none;">Download 📥</a>
        </div>
        <div style="background:#111; padding:20px; max-width:850px; margin:auto; border-radius:15px; text-align:left;">
            <h3 style="color:#0f0;">🔥 Related Movies</h3>
            {related}
        </div>
    </body>
    """

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
            # Fast Stream: 1MB Chunks for smooth buffering
            async for chunk in client.iter_download(m.video, chunk_size=1024*1024): yield chunk
        return Response(gen(), media_type="video/mp4")
    return {"error": "Not found"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=1)
