import os
from fastapi import FastAPI, Response
from telethon import TelegramClient
from fastapi.responses import HTMLResponse

# These will be fetched from the Cloud settings later
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

app = FastAPI()
client = TelegramClient('bot_session', API_ID, API_HASH)

@app.on_event("startup")
async def startup():
    await client.start(bot_token=BOT_TOKEN)

@app.get("/")
async def home():
    # Simple HTML Page with a Video Player
    html_content = """
    <html>
        <body style="background:#000; display:flex; justify-content:center; align-items:center; height:100vh; margin:0;">
            <video width="90%" height="auto" controls>
                <source src="/stream" type="video/mp4">
                Your browser does not support the video.
            </video>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/stream")
async def stream_video():
    # We will fetch the most recent video sent to the bot
    async for message in client.iter_messages('me', limit=1): # 'me' refers to saved messages or the bot itself
        if message.video:
            async def video_generator():
                async for chunk in client.iter_download(message.video, chunk_size=1024*1024):
                    yield chunk
            return Response(video_generator(), media_type="video/mp4")
    
    return {"error": "No video found. Send a video to your bot first!"}
