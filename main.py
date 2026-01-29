from fastapi import FastAPI, Query
import yt_dlp
import json
import os
import time

API_NAME = "Universal Media Downloader API"
OWNER = "@xoxhunterxd"
CONTACT = "https://t.me/xoxhunterxd"

SESSIONS_FILE = "sessions.json"
USAGE_FILE = "usage.json"

app = FastAPI(title=API_NAME)

def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def autoclean():
    sessions = load(SESSIONS_FILE)
    now = int(time.time())
    for t in list(sessions.keys()):
        exp = sessions[t]["expires"]
        if exp is not None and now > exp:
            del sessions[t]
    save(SESSIONS_FILE, sessions)

def validate_token(token):
    if not token:
        return False, None

    autoclean()
    sessions = load(SESSIONS_FILE)
    if token not in sessions:
        return False, None

    return True, sessions[token]["user_id"]

def log_usage(user_id, url):
    logs = load(USAGE_FILE)
    logs.setdefault(str(user_id), []).append({
        "time": int(time.time()),
        "url": url
    })
    save(USAGE_FILE, logs)

@app.get("/api/download")
async def download(
    url: str = Query(None),
    token: str = Query(None)
):
    ok, user_id = validate_token(token)
    if not ok:
        return {
            "status": "blocked",
            "message": "❌ Not verified",
            "contact_owner": OWNER,
            "telegram": CONTACT
        }

    if not url:
        return {"status": "error", "message": "Missing url"}

    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    log_usage(user_id, url)

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
        "auth": "Telegram verification only",
        "usage": "/api/download?token=TOKEN&url=LINK",
        "contact": CONTACT
    }
