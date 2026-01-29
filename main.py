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
CACHE_FILE = f"{BASE}/cache.json"

CACHE_TTL = 600  # seconds (10 minutes)

# ================= FILE HELPERS =================
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
    parts = msg.text.split()
    if len(parts) != 3:
        return
    uid, days = parts[1], int(parts[2])
    verified = load(VERIFIED_FILE)
    verified[uid] = {"expires": int(time.time()) + days * 86400}
    save(VERIFIED_FILE, verified)
    bot.reply_to(msg, f"✅ User {uid} verified for {days} days")

@bot.message_handler(commands=["del"])
def delete_user(msg):
    if not is_owner(msg):
        return
    uid = msg.text.split()[1]
    verified = load(VERIFIED_FILE)
    sessions = load(SESSIONS_FILE)

    verified.pop(uid, None)
    for t in list(sessions):
        if sessions[t]["user_id"] == uid:
            del sessions[t]

    save(VERIFIED_FILE, verified)
    save(SESSIONS_FILE, sessions)
    bot.reply_to(msg, f"🗑 User {uid} removed")

@bot.message_handler(commands=["remove"])
def remove_token(msg):
    if not is_owner(msg):
        return
    tok = msg.text.split()[1]
    sessions = load(SESSIONS_FILE)
    if tok in sessions:
        del sessions[tok]
        save(SESSIONS_FILE, sessions)
        bot.reply_to(msg, "🧹 Token removed")

@bot.message_handler(commands=["list"])
def list_users(msg):
    if not is_owner(msg):
        return
    autoclean()
    verified = load(VERIFIED_FILE)
    if not verified:
        bot.reply_to(msg, "No verified users")
        return
    now = int(time.time())
    text = "📋 Verified users:\n\n"
    for u, v in verified.items():
        days = max(0, (v["expires"] - now) // 86400)
        text += f"{u} — {days} days\n"
    bot.reply_to(msg, text)

@bot.message_handler(commands=["usage"])
def usage_cmd(msg):
    if not is_owner(msg):
        return
    parts = msg.text.split()
    if len(parts) != 2:
        bot.reply_to(msg, "Usage: /usage USER_ID")
        return

    uid = parts[1]
    usage = load(USAGE_FILE).get(uid, [])

    if not usage:
        bot.reply_to(msg, "No usage data")
        return

    platforms = {}
    for u in usage:
        platforms[u["platform"]] = platforms.get(u["platform"], 0) + 1

    text = f"📊 Usage for {uid}\n\nTotal: {len(usage)}\n\nPlatforms:\n"
    for p, c in platforms.items():
        text += f"- {p}: {c}\n"

    bot.reply_to(msg, text)

@bot.message_handler(commands=["token"])
def token(msg):
    autoclean()
    uid = str(msg.from_user.id)
    sessions = load(SESSIONS_FILE)

    # ONE-TOKEN-AT-A-TIME
    for t in list(sessions):
        if sessions[t]["user_id"] == uid:
            del sessions[t]

    if msg.from_user.id == OWNER_ID:
        tok = secrets.token_hex(24)
        sessions[tok] = {"user_id": uid, "expires": None}
        save(SESSIONS_FILE, sessions)
        bot.reply_to(msg, f"👑 OWNER TOKEN:\n`{tok}`", parse_mode="Markdown")
        return

    verified = load(VERIFIED_FILE)
    if uid not in verified:
        bot.reply_to(msg, "❌ Not verified")
        return

    tok = secrets.token_hex(24)
    sessions[tok] = {"user_id": uid, "expires": verified[uid]["expires"]}
    save(SESSIONS_FILE, sessions)
    bot.reply_to(msg, f"🔐 TOKEN:\n`{tok}`", parse_mode="Markdown")

@bot.message_handler(commands=["cmds"])
def cmds(msg):
    if not is_owner(msg):
        return
    bot.reply_to(
        msg,
        "👑 OWNER CMDS\n\n"
        "/verify USER_ID DAYS\n"
        "/del USER_ID\n"
        "/list\n"
        "/usage USER_ID\n"
        "/remove TOKEN\n"
        "/token\n"
        "/cmds"
    )

# ================= FASTAPI =================
app = FastAPI(title=API_NAME)

def validate(token):
    autoclean()
    sessions = load(SESSIONS_FILE)
    return token in sessions, sessions.get(token, {}).get("user_id")

def cache_get(url):
    cache = load(CACHE_FILE)
    item = cache.get(url)
    if item and time.time() - item["time"] < CACHE_TTL:
        return item["data"]
    return None

def cache_set(url, data):
    cache = load(CACHE_FILE)
    cache[url] = {"time": time.time(), "data": data}
    save(CACHE_FILE, cache)

def log_usage(uid, platform, url):
    usage = load(USAGE_FILE)
    usage.setdefault(uid, []).append({
        "time": int(time.time()),
        "platform": platform,
        "url": url
    })
    save(USAGE_FILE, usage)

@app.get("/api/download")
async def download(url: str = Query(None), token: str = Query(None)):
    ok, uid = validate(token)
    if not ok:
        return {
            "status": "blocked",
            "message": "❌ Not verified",
            "contact_owner": OWNER,
            "telegram": CONTACT
        }

    if not url:
        return {"status": "error", "message": "Missing url"}

    cached = cache_get(url)
    if cached:
        cached["cached"] = True
        return cached

    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)

    platform = info.get("extractor_key", "Unknown")

    result = {
        "status": "success",
        "platform": platform,
        "title": info.get("title"),
        "duration": info.get("duration"),
        "filesize": info.get("filesize") or info.get("filesize_approx"),
        "thumbnail": info.get("thumbnail"),
        "video": info.get("url"),
        "audio": next(
            (f["url"] for f in info.get("formats", []) if f.get("acodec") != "none"),
            None
        )
    }

    cache_set(url, result)
    log_usage(uid, platform, url)
    return result

def start_bot():
    bot.infinity_polling()

threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
