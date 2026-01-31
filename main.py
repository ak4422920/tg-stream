import os, re, uvicorn, time, random
from fastapi import FastAPI, Response, Request
from telethon import TelegramClient
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

# 1. Configuration
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
# ID check: Ensure it's an integer for Bot API
CHANNEL_ID = os.getenv('CHANNEL_ID', '-1003617955958')
OWNER_USERNAME = os.getenv('OWNER_USERNAME', 'AK_ownerbot')

try:
    CHANNEL_ID = int(str(CHANNEL_ID).strip())
except:
    pass

# --- Global Systems ---
movie_views = {}
CACHE = {"data": [], "last_update": 0}
CACHE_TIME = 600 # 10 Minutes

# --- AD CONFIG (Put your script here) ---
AD_CODE = """
<div style="background:#222; color:#0f0; padding:10px; margin:15px auto; max-width:728px; border:1px dashed #444; border-radius:10px;">
    <p style="margin:0; font-size:10px; color:#666;">SPONSORED AD</p>
    <h3 style="margin:5px 0;">🚀 Get 100GB Free Cloud Storage!</h3>
</div>
"""

# --- Helper Functions ---
def clean_name(name):
    if not name: return "Unknown"
    # Remove Season/Episode tags for grouping
    name = re.sub(r'(S\d+|E\d+|Season\s*\d+|Episode\s*\d+|Part\s*\d+)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'(@\w+|t\.me/\S+|https?://\S+|\[.*?\]|\{.*?\}|\(.*?\))', '', name)
    return name.replace('_', ' ').replace('.', ' ').strip()

def is_series(name):
    return bool(re.search(r'(S\d+|E\d+|Season|Episode|Part)', name, re.IGNORECASE))

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Using 'None' for session to avoid SQLite lock errors on Koyeb
    await client.start(bot_token=BOT_TOKEN)
    try:
        # Pre-fetch entity to avoid 'BotMethodInvalidError'
        await client.get_entity(CHANNEL_ID)
        print("✅ Bot connected to Channel successfully!")
    except Exception as e:
        print(f"⚠️ Connection Error: {e}. Check if Bot is Admin!")
    yield
    await client.disconnect()

app = FastAPI(lifespan=lifespan)
client = TelegramClient(None, API_ID, API_HASH)

async def update_cache():
    if time.time() - CACHE["last_update"] > CACHE_TIME:
        new_list = []
        try:
            async for message in client.iter_messages(CHANNEL_ID, limit=500):
                if message.video:
                    raw = getattr(message.video.attributes[0], 'file_name', 'Video')
                    new_list.append({
                        "id": message.id,
                        "raw_name": raw,
                        "c_name": clean_name(raw),
                        "is_ser": is_series(raw),
                        "size": round(message.video.size/(1024*1024), 2)
                    })
            CACHE["data"] = new_list
            CACHE["last_update"] = time.time()
        except Exception as e:
            print(f"❌ Cache Update Failed: {e}")

@app.get("/", response_class=HTMLResponse)
async def home(q: str = None, page: int = 1):
    await update_cache()
    data = CACHE["data"]
    
    # Search Logic
    if q:
        data = [i for i in data if q.lower() in i["c_name"].lower()]
    
    # Grouping Logic for Series
    grouped = {}
    for item in data:
        name = item["c_name"]
        if name not in grouped:
            grouped[name] = item
    
    final_list = list(grouped.values())
    
    # Pagination Logic (20 per page)
    per_page = 20
    total = len(final_list)
    start = (page - 1) * per_page
    paginated = final_list[start : start + per_page]

    cards_html = ""
    for itm in paginated:
        label = "SERIES" if itm["is_ser"] else "MOVIE"
        url = f"/series/{itm['c_name']}" if itm["is_ser"] else f"/watch/{itm['id']}"
        cards_html += f"""
        <div style="background:#111; margin:12px; border-radius:15px; overflow:hidden; border:1px solid #222; width:250px; display:inline-block; vertical-align:top;">
            <div style="position:relative;">
                <img src="/thumb/{itm['id']}" style="width:100%; height:150px; object-fit:cover; background:#222;">
                <span style="position:absolute; top:8px; left:8px; background:#0f0; color:#000; padding:2px 8px; border-radius:5px; font-size:10px; font-weight:bold;">{label}</span>
            </div>
            <div style="padding:15px; text-align:left;">
                <h3 style="margin:0; color:#fff; font-size:14px; height:40px; overflow:hidden;">{itm['c_name']}</h3>
                <p style="color:#666; font-size:11px; margin:10px 0;">📏 {itm['size']} MB</p>
                <a href="{url}" style="display:block; background:#0f0; color:#000; padding:10px; text-decoration:none; border-radius:8px; font-weight:bold; text-align:center;">{ "VIEW" if itm["is_ser"] else "PLAY" }</a>
            </div>
        </div>
        """

    return f"""
    <html>
    <head><title>AK OTT</title></head>
    <body style="background:#000; color:#fff; font-family:sans-serif; text-align:center; padding:20px;">
        <div style="display:flex; justify-content:space-between; align-items:center; max-width:1000px; margin:auto;">
            <h1 style="color:#0f0;">🎥 AK PREMIUM</h1>
            <a href="https://t.me/{OWNER_USERNAME}" style="background:#0088cc; color:#fff; padding:10px 20px; text-decoration:none; border-radius:10px; font-weight:bold; font-size:13px;">➕ REQUEST</a>
        </div>
        {AD_CODE}
        <form style="margin:20px;"><input name="q" placeholder="Search..." style="padding:12px; width:60%; border-radius:10px; background:#111; color:#fff; border:none;"> <button style="padding:12px 25px; background:#0f0; border:none; border-radius:10px; cursor:pointer; font-weight:bold;">Find</button></form>
        <div>{cards_html if cards_html else "No Content Found"}</div>
        <div style="margin-top:30px;">
            {f'<a href="/?page={page+1}" style="color:#0f0; text-decoration:none; border:1px solid #0f0; padding:10px 20px; border-radius:10px;">Next Page →</a>' if total > start + per_page else ""}
        </div>
    </body>
    </html>
    """

@app.get("/series/{series_name}", response_class=HTMLResponse)
async def list_episodes(series_name: str):
    await update_cache()
    eps = "".join([f'<div style="background:#111; padding:15px; margin:10px; border-radius:10px; display:flex; justify-content:space-between;"><span>{i["raw_name"]}</span><a href="/watch/{i["id"]}" style="color:#0f0; text-decoration:none; font-weight:bold;">PLAY</a></div>' for i in CACHE["data"] if i["c_name"] == series_name])
    return f"<html><body style='background:#000; color:#fff; font-family:sans-serif; padding:20px;'><h1>📺 {series_name}</h1>{eps}<br><a href='/' style='color:#0f0;'>← Back Home</a></body></html>"

@app.get("/watch/{msg_id}", response_class=HTMLResponse)
async def watch(msg_id: int):
    return f"""
    <body style="background:#000; color:#fff; text-align:center; padding:20px; font-family:sans-serif;">
        {AD_CODE}
        <video width="95%" controls autoplay style="max-width:850px; border:2px solid #0f0; border-radius:15px;"><source src="/stream/{msg_id}" type="video/mp4"></video>
        <br><br>
        <div style="display:flex; justify-content:center; gap:20px;">
            <a href="/" style="color:#0f0; text-decoration:none; font-size:18px; border:1px solid #0f0; padding:10px 25px; border-radius:10px;">← Back</a>
            <a href="/stream/{msg_id}" download style="color:#fff; text-decoration:none; font-size:18px; background:#333; padding:10px 25px; border-radius:10px;">Download 📥</a>
        </div>
        {AD_CODE}
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
            # Fast Buffering: 1MB chunks
            async for chunk in client.iter_download(m.video, chunk_size=1024*1024): yield chunk
        return Response(gen(), media_type="video/mp4")
    return {"error": "Not found"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Keep workers=1 to prevent SQLite lock on Koyeb
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=1)
