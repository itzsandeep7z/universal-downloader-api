from fastapi import FastAPI, Query
import yt_dlp
import json
import os
import time

# ================= CONFIG =================
API_NAME = "Universal Media Downloader API"
API_VERSION = "2.0.0"
DEVELOPER = "@xoxhunterxd"
CONTACT_TG = "https://t.me/xoxhunterxd"

KEYS_FILE = os.getenv("KEYS_PATH", "/tmp/keys.json")
OWNER_MASTER_KEY = os.getenv("OWNER_MASTER_KEY")

app = FastAPI(title=API_NAME)

# ================= STORAGE =================
def ensure_keys_file():
    os.makedirs(os.path.dirname(KEYS_FILE), exist_ok=True)
    if not os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "w") as f:
            json.dump({}, f)

def load_keys():
    ensure_keys_file()
    with open(KEYS_FILE, "r") as f:
        return json.load(f)

def save_keys(data):
    ensure_keys_file()
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def cleanup_expired(keys):
    now = int(time.time())
    changed = False
    for k in list(keys.keys()):
        if now > keys[k]["expires"]:
            del keys[k]
            changed = True
    return changed

# ================= KEY VALIDATION =================
def validate_key(api_key: str):
    # 🔐 OWNER MASTER KEY (HIDDEN, NO EXPIRY)
    if OWNER_MASTER_KEY and api_key == OWNER_MASTER_KEY:
        return True, None

    if not api_key:
        return False, "missing"

    keys = load_keys()

    if cleanup_expired(keys):
        save_keys(keys)

    if api_key not in keys:
        return False, "invalid"

    if int(time.time()) > keys[api_key]["expires"]:
        del keys[api_key]
        save_keys(keys)
        return False, "expired"

    keys[api_key]["used"] += 1
    save_keys(keys)
    return True, None

# ================= BLOCK RESPONSE =================
def blocked(reason):
    return {
        "status": "blocked",
        "message": {
            "missing": "❌ API key missing",
            "invalid": "❌ Invalid API key",
            "expired": "⏰ API key expired"
        }.get(reason, "❌ Access denied"),
        "help": "🔑 This API is private",
        "contact_owner": DEVELOPER,
        "telegram": CONTACT_TG
    }

# ================= API =================
@app.get("/api/download")
async def download(
    url: str = Query(None),
    key: str = Query(None)
):
    ok, reason = validate_key(key)
    if not ok:
        return blocked(reason)

    if not url:
        return {
            "status": "error",
            "message": "Missing url parameter",
            "example": "/api/download?key=APIKEY&url=MEDIA_LINK"
        }

    try:
        with yt_dlp.YoutubeDL({
            "quiet": True,
            "skip_download": True
        }) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
            "status": "success",
            "api": API_NAME,
            "version": API_VERSION,
            "developer": DEVELOPER,
            "platform": info.get("extractor_key"),
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "media_url": info.get("url")
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/")
def root():
    return {
        "api": API_NAME,
        "version": API_VERSION,
        "usage": "/api/download?key=APIKEY&url=LINK",
        "contact": CONTACT_TG
    }
