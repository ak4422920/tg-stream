import os
import asyncio
from fastapi import FastAPI, Response
from telethon import TelegramClient
from fastapi.responses import HTMLResponse

# 1. Credentials - integer conversion added to prevent crash
API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

app = FastAPI()
# Bot session setup
client = TelegramClient('bot_session', API_ID, API_HASH)

@app.on_event("startup")
async def startup():
    # Connecting to Telegram servers
    await client.start(bot_token=BOT_TOKEN)

@app.get("/")
async def home():
    # Sleek Dark Player UI
    html_content = """
    <html>
        <head>
            <title>My Movie Streamer</title>
            <style>
                body { background: #0f0f0f; color: #00ff88; font-family: sans-serif; 
                       display: flex; flex-direction: column; align-items: center; 
                       justify-content: center; height: 100vh; margin: 0; }
                video { width: 85%; max-width: 800px; border: 3px solid #00ff88; 
                        border-radius: 15px; box-shadow: 0 0 30px rgba(0, 255, 136, 0.3); }
                h1 { margin-bottom: 20px; text-shadow: 0 0 10px #00ff88; }
            </style>
        </head>
        <body>
            <h1>🎬 Now Playing</h1>
            <video controls autoplay>
                <source src="/stream" type="video/mp4">
                Your browser does not support the video.
            </video>
            <p style="color: #888; margin-top: 15px;">Send a video to your bot to update the stream.</p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/stream")
async def stream_video():
    # Bot fetches the very last message sent to it
    async for message in client.iter_messages('me', limit=1):
        if message.video:
            # This 'generator' streams chunks directly to the browser
            async def video_generator():
                async for chunk in client.iter_download(message.video, chunk_size=1024*1024):
                    yield chunk
            return Response(video_generator(), media_type="video/mp4")
    
    return {"error": "No video found. Please send a video to your bot!"}
