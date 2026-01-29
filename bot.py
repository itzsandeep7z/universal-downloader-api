import telebot
import os
import json
import secrets
import time

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

VERIFIED_FILE = "/tmp/verified.json"
SESSIONS_FILE = "/tmp/sessions.json"
USAGE_FILE = "/tmp/usage.json"

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- FILE UTILS ----------
def load(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def is_owner(msg):
    return msg.from_user.id == OWNER_ID

def autoclean():
    now = int(time.time())
    verified = load(VERIFIED_FILE)
    sessions = load(SESSIONS_FILE)

    # clean expired verified users
    for uid in list(verified.keys()):
        if now > verified[uid]["expires"]:
            del verified[uid]

    # clean expired sessions
    for tok in list(sessions.keys()):
        exp = sessions[tok]["expires"]
        if exp is not None and now > exp:
            del sessions[tok]

    save(VERIFIED_FILE, verified)
    save(SESSIONS_FILE, sessions)

# ---------- VERIFY USER ----------
@bot.message_handler(commands=["verify"])
def verify(message):
    if not is_owner(message):
        return

    parts = message.text.split()
    if len(parts) != 3 or not parts[2].isdigit():
        bot.reply_to(message, "Usage: /verify USER_ID DAYS")
        return

    uid = parts[1]
    days = int(parts[2])
    expires = int(time.time()) + days * 86400

    verified = load(VERIFIED_FILE)
    verified[uid] = {"expires": expires}
    save(VERIFIED_FILE, verified)

    bot.reply_to(message, f"✅ User {uid} verified for {days} days")

# ---------- DELETE USER ----------
@bot.message_handler(commands=["del"])
def delete_user(message):
    if not is_owner(message):
        return

    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /del USER_ID")
        return

    uid = parts[1]
    verified = load(VERIFIED_FILE)
    sessions = load(SESSIONS_FILE)

    if uid in verified:
        del verified[uid]

    removed = 0
    for t in list(sessions.keys()):
        if sessions[t]["user_id"] == uid:
            del sessions[t]
            removed += 1

    save(VERIFIED_FILE, verified)
    save(SESSIONS_FILE, sessions)

    bot.reply_to(message, f"🗑 User {uid} removed | Tokens revoked: {removed}")

# ---------- REMOVE TOKEN ----------
@bot.message_handler(commands=["remove"])
def remove_token(message):
    if not is_owner(message):
        return

    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /remove TOKEN")
        return

    tok = parts[1]
    sessions = load(SESSIONS_FILE)

    if tok in sessions:
        del sessions[tok]
        save(SESSIONS_FILE, sessions)
        bot.reply_to(message, "🧹 Token removed")
    else:
        bot.reply_to(message, "❌ Token not found")

# ---------- LIST VERIFIED USERS ----------
@bot.message_handler(commands=["list"])
def list_verified(message):
    if not is_owner(message):
        return

    autoclean()
    verified = load(VERIFIED_FILE)

    if not verified:
        bot.reply_to(message, "No verified users")
        return

    now = int(time.time())
    text = "📋 Verified users:\n\n"
    for uid, v in verified.items():
        days = max(0, (v["expires"] - now) // 86400)
        text += f"{uid} — {days} days left\n"

    bot.reply_to(message, text)

# ---------- GENERATE TOKEN ----------
@bot.message_handler(commands=["token"])
def token(message):
    autoclean()
    uid = str(message.from_user.id)
    now = int(time.time())

    sessions = load(SESSIONS_FILE)

    # OWNER → no expiry
    if message.from_user.id == OWNER_ID:
        tok = secrets.token_hex(24)
        sessions[tok] = {"user_id": uid, "expires": None}
        save(SESSIONS_FILE, sessions)
        bot.reply_to(message, f"👑 OWNER TOKEN:\n`{tok}`", parse_mode="Markdown")
        return

    verified = load(VERIFIED_FILE)
    if uid not in verified or now > verified[uid]["expires"]:
        bot.reply_to(message, "❌ You are not verified")
        return

    tok = secrets.token_hex(24)
    sessions[tok] = {"user_id": uid, "expires": verified[uid]["expires"]}
    save(SESSIONS_FILE, sessions)

    days = (verified[uid]["expires"] - now) // 86400
    bot.reply_to(message, f"🔐 Token valid {days} days:\n`{tok}`", parse_mode="Markdown")

# ---------- OWNER COMMANDS ----------
@bot.message_handler(commands=["cmds"])
def cmds(message):
    if not is_owner(message):
        return
    bot.reply_to(
        message,
        "👑 OWNER CMDS\n"
        "/verify USER_ID DAYS\n"
        "/del USER_ID\n"
        "/list\n"
        "/remove TOKEN\n"
        "/token\n"
        "/cmds"
    )

bot.infinity_polling()
