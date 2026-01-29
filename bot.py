import telebot
import json
import os
import secrets
import time

BOT_TOKEN = "8496179658:AAFUMyVFhi_T2aVC7QSyBaqKNCvmjP-yH4o"
OWNER_ID = 6021047784
KEYS_FILE = "keys.json"

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- UTILS ----------
def is_owner(message):
    return message.from_user.id == OWNER_ID

def load_keys():
    if not os.path.exists(KEYS_FILE):
        return {}
    with open(KEYS_FILE, "r") as f:
        return json.load(f)

def save_keys(data):
    with open(KEYS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------- /cmds (OWNER ONLY) ----------
@bot.message_handler(commands=["cmds"])
def cmds(message):
    if not is_owner(message):
        bot.reply_to(message, "❌ Owner only command.")
        return

    bot.reply_to(
        message,
        "🧠 **OWNER COMMANDS LIST**\n\n"
        "🔐 `/getkey DAYS` — Generate API key with expiry\n"
        "📋 `/list` — List all API keys\n"
        "🗑 `/revoke API_KEY` — Revoke an API key\n"
        "📊 `/used` — Show per-key usage\n"
        "📈 `/stat` — Show global API stats\n"
        "📖 `/cmds` — Show this command list\n",
        parse_mode="Markdown"
    )

# ---------- /getkey <days> ----------
@bot.message_handler(commands=["getkey"])
def get_key(message):
    if not is_owner(message):
        bot.reply_to(message, "❌ Owner only command.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        bot.reply_to(message, "⚠️ Usage:\n/getkey DAYS\nExample:\n/getkey 30")
        return

    days = int(parts[1])
    now = int(time.time())
    expires = now + (days * 86400)

    api_key = secrets.token_hex(16)

    keys = load_keys()
    keys[api_key] = {
        "created": now,
        "expires": expires,
        "used": 0
    }
    save_keys(keys)

    bot.reply_to(
        message,
        f"🔐 **API KEY GENERATED**\n\n"
        f"`{api_key}`\n\n"
        f"⏳ Valid for: **{days} days**\n"
        f"📌 Header:\n`X-API-Key: {api_key}`",
        parse_mode="Markdown"
    )

# ---------- /list ----------
@bot.message_handler(commands=["list"])
def list_keys(message):
    if not is_owner(message):
        bot.reply_to(message, "❌ Owner only command.")
        return

    keys = load_keys()
    if not keys:
        bot.reply_to(message, "📭 No API keys.")
        return

    text = "📋 **API KEYS**\n\n"
    for i, (k, v) in enumerate(keys.items(), 1):
        exp_days = max(0, (v["expires"] - int(time.time())) // 86400)
        text += f"{i}. `{k}` | ⏳ {exp_days} days | ⚡ {v['used']}\n"

    bot.reply_to(message, text, parse_mode="Markdown")

# ---------- /revoke ----------
@bot.message_handler(commands=["revoke"])
def revoke(message):
    if not is_owner(message):
        bot.reply_to(message, "❌ Owner only command.")
        return

    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "⚠️ Usage:\n/revoke API_KEY")
        return

    api_key = parts[1]
    keys = load_keys()

    if api_key not in keys:
        bot.reply_to(message, "❌ API key not found.")
        return

    del keys[api_key]
    save_keys(keys)

    bot.reply_to(message, f"🗑 **API key revoked**:\n`{api_key}`", parse_mode="Markdown")

# ---------- /used ----------
@bot.message_handler(commands=["used"])
def used(message):
    if not is_owner(message):
        bot.reply_to(message, "❌ Owner only command.")
        return

    keys = load_keys()
    if not keys:
        bot.reply_to(message, "📭 No usage data.")
        return

    text = "📊 **API USAGE**\n\n"
    for k, v in keys.items():
        text += f"`{k}` → {v['used']} requests\n"

    bot.reply_to(message, text, parse_mode="Markdown")

# ---------- /stat ----------
@bot.message_handler(commands=["stat"])
def stat(message):
    if not is_owner(message):
        bot.reply_to(message, "❌ Owner only command.")
        return

    keys = load_keys()
    total_keys = len(keys)
    total_used = sum(v["used"] for v in keys.values())

    bot.reply_to(
        message,
        f"📈 **API STATISTICS**\n\n"
        f"🔑 Total Keys: **{total_keys}**\n"
        f"⚡ Total Requests: **{total_used}**",
        parse_mode="Markdown"
    )

bot.infinity_polling()
