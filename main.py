from fastapi import FastAPI, Query, Header, HTTPException
import yt_dlp
import json
import os
import time

API_NAME = "Universal Media Downloader API"
API_VERSION = "1.2.0"
DEVELOPER = "@xoxhunterxd"

KEYS_FILE = "keys.json"

app = FastAPI(title=API_NAME)

# ---------- KEY UTILS ----------
def load_keys():
    if not os.path.exists(KEYS_FILE):
        return {}
    with open(KEYS_FILE, "r") as f:
        return json.load(f)

def save_keys(data):
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def validate_key(api_key: str):
    keys = load_keys()

    if api_key not in keys:
        return False, "Invalid API key"

    key_data = keys[api_key]
    now = int(time.time())

    if now > key_data["expires"]:
        return False, "API key expired"

    # increment usage
    key_data["used"] += 1
    keys[api_key] = key_data
    save_keys(keys)

    return True, None

# ---------- UNIVERSAL API ----------
@app.get("/api/download")
async def download_api(
    url: str = Query(..., description="Any public social media URL"),
    x_api_key: str = Header(None)
):
    if not x_api_key:
        raise HTTPException(status_code=403, detail="API key required")

    valid, error = validate_key(x_api_key)
    if not valid:
        raise HTTPException(status_code=403, detail=error)

    ydl_opts = {
        "quiet": True,
        "skip_download": True
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
# ---------- RUN SERVER ----------
