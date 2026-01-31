import os
import asyncio
import uvicorn
from fastapi import FastAPI, Response
from telethon import TelegramClient
from fastapi.responses import HTMLResponse

# 1. Credentials - Integers for safety
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

app = FastAPI()
client = TelegramClient('bot_session', API_ID, API_HASH)

@app.on_event("startup")
async def startup():
    await client.start(bot_token=BOT_TOKEN)

@app.get("/")
async def home():
    html_content = """
    <html>
        <head>
            <title>My Streamer</title>
            <style>
                body { background: #000; color: #0f0; font-family: sans-serif; text-align: center; padding-top: 50px; }
                video { width: 80%; border: 2px solid #0f0; border-radius: 10px; }
            </style>
        </head>
        <body>
            <h1>🎬 Bot is Live!</h1>
            <video controls autoplay><source src="/stream" type="video/mp4"></video>
            <p>Send a video to your bot to test.</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/stream")
async def stream_video():
    async for message in client.iter_messages('me', limit=1):
        if message.video:
            async def video_generator():
                async for chunk in client.iter_download(message.video, chunk_size=1024*1024):
                    yield chunk
            return Response(video_generator(), media_type="video/mp4")
    return {"error": "No video found"}

# --- YE HAI MASTER TRICK ---
if __name__ == "__main__":
    # Koyeb automatically gives a PORT variable
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
