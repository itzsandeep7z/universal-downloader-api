from fastapi import FastAPI, Query
import yt_dlp
import json
import os
import time

# ================= CONFIG =================
API_NAME = "Universal Media Downloader API"
OWNER = "@xoxhunterxd"
CONTACT = "https://t.me/xoxhunterxd"

OWNER_TOKEN = os.getenv("OWNER_TOKEN")
SESSIONS_FILE = "sessions.json"

app = FastAPI(title=API_NAME)

# ================= SESSION UTILS =================
def load_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return {}
    with open(SESSIONS_FILE, "r") as f:
        return json.load(f)

def save_sessions(data):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def validate_token(token: str):
    # 👑 OWNER TOKEN (NO EXPIRY)
    if OWNER_TOKEN and token == OWNER_TOKEN:
        return True

    if not token:
        return False

    sessions = load_sessions()
    now = int(time.time())

    if token not in sessions:
        return False

    if now > sessions[token]["expires"]:
        del sessions[token]
        save_sessions(sessions)
        return False

    return True

# ================= API =================
@app.get("/api/download")
async def download(
    url: str = Query(None),
    token: str = Query(None)
):
    if not validate_token(token):
        return {
            "status": "blocked",
            "message": "❌ Not verified",
            "help": "Verify via Telegram bot",
            "contact_owner": OWNER,
            "telegram": CONTACT
        }

    if not url:
        return {"status": "error", "message": "Missing url"}

    with yt_dlp.YoutubeDL({
        "quiet": True,
        "skip_download": True
    }) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "status": "success",
        "title": info.get("title"),
        "thumbnail": info.get("thumbnail"),
        "media_url": info.get("url")
    }

@app.get("/")
def root():
    return {
        "api": API_NAME,
        "auth": "Telegram verified users + owner token",
        "usage": "/api/download?token=TOKEN&url=LINK",
        "contact": CONTACT
    }
