import threading
import time
import os
import json
import secrets

import telebot
from fastapi import FastAPI, Query
import yt_dlp
import uvicorn

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

API_NAME = "Universal Media Downloader API"
OWNER = "@xoxhunterxd"
CONTACT = "https://t.me/xoxhunterxd"

BASE = "/tmp"
VERIFIED_FILE = f"{BASE}/verified.json"
SESSIONS_FILE = f"{BASE}/sessions.json"
USAGE_FILE = f"{BASE}/usage.json"

# ================= FILE UTILS =================
def ensure(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({}, f)

def load(path):
    ensure(path)
    with open(path, "r") as f:
        return json.load(f)

def save(path, data):
    ensure(path)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def autoclean():
    now = int(time.time())
    verified = load(VERIFIED_FILE)
    sessions = load(SESSIONS_FILE)

    for u in list(verified):
        if now > verified[u]["expires"]:
            del verified[u]

    for t in list(sessions):
        exp = sessions[t]["expires"]
        if exp is not None and now > exp:
            del sessions[t]

    save(VERIFIED_FILE, verified)
    save(SESSIONS_FILE, sessions)

# ================= TELEGRAM BOT =================
bot = telebot.TeleBot(BOT_TOKEN)

def is_owner(msg):
    return msg.from_user.id == OWNER_ID

@bot.message_handler(commands=["verify"])
def verify(msg):
    if not is_owner(msg):
        return
    _, uid, days = msg.text.split()
    verified = load(VERIFIED_FILE)
    verified[uid] = {"expires": int(time.time()) + int(days)*86400}
    save(VERIFIED_FILE, verified)
    bot.reply_to(msg, "✅ Verified")

@bot.message_handler(commands=["token"])
def token(msg):
    autoclean()
    uid = str(msg.from_user.id)
    sessions = load(SESSIONS_FILE)

    if msg.from_user.id == OWNER_ID:
        t = secrets.token_hex(24)
        sessions[t] = {"user_id": uid, "expires": None}
        save(SESSIONS_FILE, sessions)
        bot.reply_to(msg, f"👑 `{t}`", parse_mode="Markdown")
        return

    verified = load(VERIFIED_FILE)
    if uid not in verified:
        bot.reply_to(msg, "❌ Not verified")
        return

    t = secrets.token_hex(24)
    sessions[t] = {"user_id": uid, "expires": verified[uid]["expires"]}
    save(SESSIONS_FILE, sessions)
    bot.reply_to(msg, f"🔐 `{t}`", parse_mode="Markdown")

# ================= FASTAPI =================
app = FastAPI(title=API_NAME)

def validate(token):
    autoclean()
    sessions = load(SESSIONS_FILE)
    return token in sessions

@app.get("/api/download")
async def download(url: str = Query(None), token: str = Query(None)):
    if not validate(token):
        return {
            "status": "blocked",
            "message": "❌ Not verified",
            "contact_owner": OWNER,
            "telegram": CONTACT
        }

    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "status": "success",
        "title": info.get("title"),
        "media_url": info.get("url")
    }

# ================= RUN BOTH =================
def start_bot():
    bot.infinity_polling()

threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
