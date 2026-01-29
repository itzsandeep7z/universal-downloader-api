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
def load_file(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def save_file(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

# ---------- OWNER CHECK ----------
def is_owner(msg):
    return msg.from_user.id == OWNER_ID

# ---------- COMMANDS ----------
@bot.message_handler(commands=["verify"])
def verify_user(message):
    if not is_owner(message):
        return

    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /verify USER_ID")
        return

    user_id = parts[1]
    verified = load_file(VERIFIED_FILE)
    verified[user_id] = True
    save_file(VERIFIED_FILE, verified)

    bot.reply_to(message, f"✅ User {user_id} verified")

@bot.message_handler(commands=["token"])
def get_token(message):
    user_id = str(message.from_user.id)
    verified = load_file(VERIFIED_FILE)

    if user_id not in verified:
        bot.reply_to(message, "❌ You are not verified")
        return

    token = secrets.token_hex(16)
    sessions = load_file(SESSIONS_FILE)

    sessions[token] = {
        "user_id": user_id,
        "expires": int(time.time()) + 600  # 10 minutes
    }

    save_file(SESSIONS_FILE, sessions)

    bot.reply_to(
        message,
        f"🔐 Access token (10 min):\n`{token}`",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["cmds"])
def cmds(message):
    if not is_owner(message):
        return

    bot.reply_to(
        message,
        "/verify USER_ID – verify user\n"
        "/token – generate API token\n"
        "/cmds – owner commands"
    )

bot.infinity_polling()
