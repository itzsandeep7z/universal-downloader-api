import telebot
import os
import json
import secrets
import time

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

VERIFIED_FILE = "verified.json"
SESSIONS_FILE = "sessions.json"

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

# ---------- VERIFY USER ----------
@bot.message_handler(commands=["verify"])
def verify(message):
    if not is_owner(message):
        return

    parts = message.text.split()
    if len(parts) != 3 or not parts[2].isdigit():
        bot.reply_to(message, "Usage: /verify USER_ID DAYS")
        return

    user_id = parts[1]
    days = int(parts[2])

    expires = int(time.time()) + days * 86400
    verified = load(VERIFIED_FILE)

    verified[user_id] = {
        "expires": expires
    }

    save(VERIFIED_FILE, verified)
    bot.reply_to(message, f"✅ User {user_id} verified for {days} days")

# ---------- GENERATE TOKEN ----------
@bot.message_handler(commands=["token"])
def token(message):
    user_id = str(message.from_user.id)
    now = int(time.time())

    # OWNER → NO EXPIRY
    if message.from_user.id == OWNER_ID:
        token = secrets.token_hex(24)
        sessions = load(SESSIONS_FILE)
        sessions[token] = {
            "user_id": user_id,
            "expires": None  # no expiry
        }
        save(SESSIONS_FILE, sessions)

        bot.reply_to(
            message,
            f"👑 OWNER TOKEN (NO EXPIRY):\n`{token}`",
            parse_mode="Markdown"
        )
        return

    # NORMAL USER
    verified = load(VERIFIED_FILE)

    if user_id not in verified:
        bot.reply_to(message, "❌ You are not verified")
        return

    if now > verified[user_id]["expires"]:
        del verified[user_id]
        save(VERIFIED_FILE, verified)
        bot.reply_to(message, "⏰ Your verification expired")
        return

    token = secrets.token_hex(24)
    sessions = load(SESSIONS_FILE)

    sessions[token] = {
        "user_id": user_id,
        "expires": verified[user_id]["expires"]
    }

    save(SESSIONS_FILE, sessions)

    left_days = (verified[user_id]["expires"] - now) // 86400

    bot.reply_to(
        message,
        f"🔐 Token generated\n"
        f"Valid for {left_days} days\n\n"
        f"`{token}`",
        parse_mode="Markdown"
    )

# ---------- OWNER COMMANDS ----------
@bot.message_handler(commands=["cmds"])
def cmds(message):
    if not is_owner(message):
        return

    bot.reply_to(
        message,
        "/verify USER_ID DAYS – verify user\n"
        "/token – get owner token\n"
        "/cmds – show commands"
    )

bot.infinity_polling()
