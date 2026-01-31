import os
import asyncio
import uvicorn
from fastapi import FastAPI, Response
from telethon import TelegramClient
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

# 1. Credentials
API_ID = int(os.getenv('API_ID', 0))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# --- Lifespan (Modern & Clean) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 'None' use kiya hai taaki SQLite database lock na ho
    await client.start(bot_token=BOT_TOKEN)
    print("✅ Bot Started Successfully in Memory!")
    yield
    await client.disconnect()

app = FastAPI(lifespan=lifespan)
# Session name 'None' means it stays in RAM (No file locking)
client = TelegramClient(None, API_ID, API_HASH)

@app.get("/")
async def home():
    return HTMLResponse("""
    <body style="background:#000;color:#0f0;display:flex;flex-direction:column;justify-content:center;align-items:center;height:100vh;margin:0;font-family:sans-serif;">
        <h1>🎬 Bot is Online</h1>
        <video width="80%" controls autoplay style="border:2px solid #0f0;border-radius:10px;">
            <source src="/stream" type="video/mp4">
        </video>
        <p>Send a video to the bot and refresh this page!</p>
    </body>
    """)

@app.get("/stream")
async def stream_video():
    # 'me' refers to the bot's own chat
    async for message in client.iter_messages('me', limit=1):
        if message.video:
            async def video_generator():
                async for chunk in client.iter_download(message.video, chunk_size=1024*1024):
                    yield chunk
            return Response(video_generator(), media_type="video/mp4")
    return {"error": "No video found in bot chat"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # Workers=1 rakha hai taaki crash na ho
    uvicorn.run("main:app", host="0.0.0.0", port=port, workers=1)
