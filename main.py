from fastapi import FastAPI, Query
import yt_dlp
import json
import os
import time

# ================= CONFIG =================
API_NAME = "Universal Media Downloader API"
API_VERSION = "1.4.0"
DEVELOPER = "@xoxhunterxd"
CONTACT_TG = "https://t.me/xoxhunterxd"

KEYS_FILE = "keys.json"

app = FastAPI(title=API_NAME)

# ================= KEY UTILITIES =================
def load_keys():
    if not os.path.exists(KEYS_FILE):
        return {}
    with open(KEYS_FILE, "r") as f:
        return json.load(f)

def save_keys(data):
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def cleanup_expired():
    keys = load_keys()
    now = int(time.time())
    changed = False

    for k in list(keys.keys()):
        if now > keys[k]["expires"]:
            del keys[k]
            changed = True

    if changed:
        save_keys(keys)

def validate_key(api_key: str):
    cleanup_expired()
    keys = load_keys()
    now = int(time.time())

    if not api_key:
        return False, "missing"

    if api_key not in keys:
        return False, "invalid"

    if now > keys[api_key]["expires"]:
        return False, "expired"

    # increment usage
    keys[api_key]["used"] += 1
    save_keys(keys)

    return True, None

# ================= STYLISH BLOCK RESPONSE =================
def blocked_response(reason):
    messages = {
        "missing": "❌ API key missing",
        "invalid": "❌ Invalid API key",
        "expired": "⏰ API key expired"
    }

    return {
        "status": "blocked",
        "reason": reason,
        "message": messages.get(reason, "❌ Access denied"),
        "help": "🔑 This API is protected. Contact owner for access.",
        "contact_owner": DEVELOPER,
        "telegram": CONTACT_TG
    }

# ================= MAIN API =================
@app.get("/api/download")
async def download_api(
    url: str = Query(None, description="Any public social media URL"),
    key: str = Query(None, description="API key")
):
    valid, reason = validate_key(key)
    if not valid:
        return blocked_response(reason)

    if not url:
        return {
            "status": "error",
            "message": "❌ Missing url parameter",
            "example": "/api/download?key=APIKEY&url=MEDIA_LINK"
        }

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "nocheckcertificate": True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
            "status": "success",
            "api_name": API_NAME,
            "api_version": API_VERSION,
            "developer": DEVELOPER,
            "platform": info.get("extractor_key"),
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "media_url": info.get("url")
        }

    except Exception as e:
        return {
            "status": "error",
            "api_name": API_NAME,
            "api_version": API_VERSION,
            "developer": DEVELOPER,
            "message": str(e)
        }

# ================= ROOT INFO (OPTIONAL) =================
@app.get("/")
async def root():
    return {
        "api": API_NAME,
        "version": API_VERSION,
        "developer": DEVELOPER,
        "contact": CONTACT_TG,
        "usage": "/api/download?key=APIKEY&url=MEDIA_LINK"
    }
