import os
import time
import json
import secrets
import threading

import yt_dlp
import telebot
import uvicorn
from fastapi import FastAPI, Query
from sqlalchemy import (
    create_engine, Column, Integer, String, BigInteger, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
DATABASE_URL = os.getenv("DATABASE_URL")

API_NAME = "Universal Downloader API"
OWNER = "@xoxhunterxd"
CONTACT = "https://t.me/xoxhunterxd"

CACHE_TTL = 600  # 10 minutes

# ================== DATABASE ==================
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class VerifiedUser(Base):
    __tablename__ = "verified_users"
    user_id = Column(String, primary_key=True)
    expires = Column(BigInteger)


class Token(Base):
    __tablename__ = "tokens"
    token = Column(String, primary_key=True)
    user_id = Column(String)
    expires = Column(BigInteger, nullable=True)


class UsageLog(Base):
    __tablename__ = "usage_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    platform = Column(String)
    url = Column(Text)
    time = Column(BigInteger)


class Cache(Base):
    __tablename__ = "cache"
    url = Column(Text, primary_key=True)
    response = Column(Text)
    time = Column(BigInteger)


Base.metadata.create_all(engine)

# ================== TELEGRAM BOT ==================
bot = telebot.TeleBot(BOT_TOKEN)


def is_owner(m):
    return m.from_user.id == OWNER_ID


@bot.message_handler(commands=["cmds"])
def cmds(m):
    if not is_owner(m):
        return
    bot.reply_to(
        m,
        "👑 OWNER CMDS\n\n"
        "/verify USER_ID DAYS\n"
        "/del USER_ID\n"
        "/list\n"
        "/usage USER_ID\n"
        "/remove TOKEN\n"
        "/token\n"
        "/cmds"
    )


@bot.message_handler(commands=["verify"])
def verify(m):
    if not is_owner(m):
        return
    _, uid, days = m.text.split()
    db = Session()
    db.merge(
        VerifiedUser(
            user_id=uid,
            expires=int(time.time()) + int(days) * 86400
        )
    )
    db.commit()
    db.close()
    bot.reply_to(m, f"✅ Verified {uid} for {days} days")


@bot.message_handler(commands=["del"])
def delete_user(m):
    if not is_owner(m):
        return
    uid = m.text.split()[1]
    db = Session()
    db.query(VerifiedUser).filter_by(user_id=uid).delete()
    db.query(Token).filter_by(user_id=uid).delete()
    db.commit()
    db.close()
    bot.reply_to(m, f"🗑 Removed {uid}")


@bot.message_handler(commands=["list"])
def list_users(m):
    if not is_owner(m):
        return
    db = Session()
    users = db.query(VerifiedUser).all()
    now = int(time.time())
    text = "📋 VERIFIED USERS\n\n"
    for u in users:
        days = max(0, (u.expires - now) // 86400)
        text += f"{u.user_id} → {days} days\n"
    db.close()
    bot.reply_to(m, text or "No users")


@bot.message_handler(commands=["usage"])
def usage(m):
    if not is_owner(m):
        return
    uid = m.text.split()[1]
    db = Session()
    logs = db.query(UsageLog).filter_by(user_id=uid).all()
    db.close()
    text = f"📊 Usage for {uid}\nTotal: {len(logs)}"
    bot.reply_to(m, text)


@bot.message_handler(commands=["remove"])
def remove_token(m):
    if not is_owner(m):
        return
    tok = m.text.split()[1]
    db = Session()
    db.query(Token).filter_by(token=tok).delete()
    db.commit()
    db.close()
    bot.reply_to(m, "🧹 Token removed")


@bot.message_handler(commands=["token"])
def token_cmd(m):
    uid = str(m.from_user.id)
    db = Session()

    # one-token-at-a-time
    db.query(Token).filter_by(user_id=uid).delete()

    if m.from_user.id == OWNER_ID:
        t = secrets.token_hex(24)
        db.add(Token(token=t, user_id=uid, expires=None))
        db.commit()
        db.close()
        bot.reply_to(m, f"👑 OWNER TOKEN\n`{t}`", parse_mode="Markdown")
        return

    user = db.query(VerifiedUser).filter_by(user_id=uid).first()
    if not user or user.expires < int(time.time()):
        db.close()
        bot.reply_to(m, "❌ Not verified")
        return

    t = secrets.token_hex(24)
    db.add(Token(token=t, user_id=uid, expires=user.expires))
    db.commit()
    db.close()
    bot.reply_to(m, f"🔐 TOKEN\n`{t}`", parse_mode="Markdown")


# ================== FASTAPI ==================
app = FastAPI(title=API_NAME)


@app.get("/api/download")
async def download(url: str = Query(None), token: str = Query(None)):
    if not url or not token:
        return {"status": "error", "message": "Missing parameters"}

    db = Session()
    t = db.query(Token).filter_by(token=token).first()
    if not t or (t.expires and t.expires < int(time.time())):
        db.close()
        return {
            "status": "blocked",
            "message": "❌ Not verified",
            "contact_owner": OWNER,
            "telegram": CONTACT
        }

    # -------- CACHE CHECK --------
    cached = db.query(Cache).filter_by(url=url).first()
    if cached and int(time.time()) - cached.time < CACHE_TTL:
        db.close()
        return json.loads(cached.response)

    # -------- YT-DLP --------
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "format": "bestvideo+bestaudio/best"
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = info.get("formats", [])
    video_url = None
    audio_url = None

    for f in formats:
        if f.get("vcodec") != "none" and f.get("url"):
            video_url = f["url"]
            break

    for f in formats:
        if f.get("acodec") != "none" and f.get("vcodec") == "none" and f.get("url"):
            audio_url = f["url"]
            break

    result = {
        "status": "success",
        "platform": info.get("extractor_key"),
        "title": info.get("title"),
        "duration": info.get("duration"),
        "thumbnail": info.get("thumbnail"),
        "video": video_url,
        "audio": audio_url
    }

    # -------- CACHE UPSERT (FIXED) --------
    if cached:
        cached.response = json.dumps(result)
        cached.time = int(time.time())
    else:
        db.add(
            Cache(
                url=url,
                response=json.dumps(result),
                time=int(time.time())
            )
        )

    db.add(
        UsageLog(
            user_id=t.user_id,
            platform=result["platform"],
            url=url,
            time=int(time.time())
        )
    )

    db.commit()
    db.close()
    return result


# ================== START BOTH ==================
def start_bot():
    bot.infinity_polling()


threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
