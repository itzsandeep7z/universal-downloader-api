import telebot
import json
import os
import secrets
import time

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
KEYS_FILE = os.getenv("KEYS_PATH", "/tmp/keys.json")

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- STORAGE (FIXED) ----------
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

def cleanup_expired():
    keys = load_keys()
    now = int(time.time())
    removed = 0

    for k in list(keys.keys()):
        if now > keys[k]["expires"]:
            del keys[k]
            removed += 1

    if removed:
        save_keys(keys)

    return removed

# ---------- UTILS ----------
def is_owner(message):
    return message.from_user.id == OWNER_ID

# ---------- /cmds ----------
@bot.message_handler(commands=["cmds"])
def cmds(message):
    if not is_owner(message):
        return

    bot.reply_to(
        message,
        "🧠 **OWNER COMMANDS**\n\n"
        "/getkey DAYS – create key\n"
        "/del KEY – delete key\n"
        "/extend KEY DAYS – extend expiry\n"
        "/info KEY – key details\n"
        "/reset KEY – reset usage\n"
        "/list – list all keys\n"
        "/stats – global stats\n"
        "/wipeexpired – remove expired keys\n"
        "/cmds – show commands",
        parse_mode="Markdown"
    )

# ---------- /getkey ----------
@bot.message_handler(commands=["getkey"])
def getkey(message):
    if not is_owner(message):
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.reply_to(message, "Usage: /getkey DAYS")
        return

    days = int(parts[1])
    now = int(time.time())
    api_key = secrets.token_hex(16)

    keys = load_keys()
    keys[api_key] = {
        "created": now,
        "expires": now + days * 86400,
        "used": 0
    }
    save_keys(keys)

    bot.reply_to(message, f"🔐 Key created:\n`{api_key}`", parse_mode="Markdown")

# ---------- /del ----------
@bot.message_handler(commands=["del"])
def delete_key(message):
    if not is_owner(message):
        return

    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /del API_KEY")
        return

    keys = load_keys()
    if parts[1] not in keys:
        bot.reply_to(message, "❌ Key not found")
        return

    del keys[parts[1]]
    save_keys(keys)
    bot.reply_to(message, "🗑 Key deleted")

# ---------- /extend ----------
@bot.message_handler(commands=["extend"])
def extend_key(message):
    if not is_owner(message):
        return

    parts = message.text.split()
    if len(parts) != 3 or not parts[2].isdigit():
        bot.reply_to(message, "Usage: /extend KEY DAYS")
        return

    keys = load_keys()
    key = parts[1]
    days = int(parts[2])

    if key not in keys:
        bot.reply_to(message, "❌ Key not found")
        return

    keys[key]["expires"] += days * 86400
    save_keys(keys)

    bot.reply_to(message, f"⏳ Extended {days} days")

# ---------- /info ----------
@bot.message_handler(commands=["info"])
def info(message):
    if not is_owner(message):
        return

    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "Usage: /info KEY")
        return

    keys = load_keys()
    key = parts[1]

    if key not in keys:
        bot.reply_to(message, "❌ Key not found")
        return

    data = keys[key]
    left = max(0, (data["expires"] - int(time.time())) // 86400)

    bot.reply_to(
        message,
        f"🔑 `{key}`\nUsed: {data['used']}\nDays left: {left}",
        parse_mode="Markdown"
    )

# ---------- /reset ----------
@bot.message_handler(commands=["reset"])
def reset(message):
    if not is_owner(message):
        return

    parts = message.text.split()
    if len(parts) != 2:
        return

    keys = load_keys()
    if parts[1] in keys:
        keys[parts[1]]["used"] = 0
        save_keys(keys)
        bot.reply_to(message, "♻ Usage reset")

# ---------- /list ----------
@bot.message_handler(commands=["list"])
def list_keys(message):
    if not is_owner(message):
        return

    cleanup_expired()
    keys = load_keys()

    if not keys:
        bot.reply_to(message, "No keys")
        return

    text = "📋 **Keys**\n\n"
    for k, v in keys.items():
        days = max(0, (v["expires"] - int(time.time())) // 86400)
        text += f"`{k}` | {days}d | {v['used']}\n"

    bot.reply_to(message, text, parse_mode="Markdown")

# ---------- /stats ----------
@bot.message_handler(commands=["stats"])
def stats(message):
    if not is_owner(message):
        return

    cleanup_expired()
    keys = load_keys()

    total_keys = len(keys)
    total_hits = sum(v["used"] for v in keys.values())

    bot.reply_to(
        message,
        f"📊 Stats\n\nKeys: {total_keys}\nRequests: {total_hits}"
    )

# ---------- /wipeexpired ----------
@bot.message_handler(commands=["wipeexpired"])
def wipe(message):
    if not is_owner(message):
        return

    removed = cleanup_expired()
    bot.reply_to(message, f"🧹 Removed {removed} expired keys")

bot.infinity_polling()
