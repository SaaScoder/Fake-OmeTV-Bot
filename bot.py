import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ChatInviteLink
from telegram.ext import Updater, CommandHandler, ChatMemberHandler
from fastapi import FastAPI
import threading

# === Load environment variables ===
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
PRIVATE_GROUP = os.getenv("PRIVATE_GROUP")
PORT = int(os.getenv("PORT", 10000))

# === In-memory storage ===
user_progress = {}
user_invite_links = {}

# === Telegram helper ===
def send_progress(updater, user_id):
    progress = user_progress.get(user_id, 0)
    if progress < 2:
        # Haal invite link op van deze gebruiker
        link = next((l for l, inviter in user_invite_links.items() if inviter == user_id), None)
        keyboard = [[InlineKeyboardButton(f"Share to unlock ({progress}/2)", url=link)]]
        text = "Please share this channel with 2 friends to unlock the group:"
    else:
        keyboard = [[InlineKeyboardButton("Open de groep", url=PRIVATE_GROUP)]]
        text = "✅ Je hebt 2 vrienden toegevoegd! Klik hieronder voor toegang."
    try:
        updater.bot.send_message(chat_id=user_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        print(f"❌ Kan user {user_id} geen privébericht sturen: {e}")

# === Chat member handler ===
def welcome(update, context):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        user_id = member.new_chat_member.user.id
        if user_id not in user_progress:
            user_progress[user_id] = 0
            invite = context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, creates_join_request=False, name=f"invite_{user_id}")
            user_invite_links[invite.invite_link] = user_id
        send_progress(context.updater, user_id)

def track_invite(update, context):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        if member.invite_link and member.invite_link.invite_link in user_invite_links:
            inviter_id = user_invite_links[member.invite_link.invite_link]
            user_progress[inviter_id] = min(user_progress[inviter_id] + 1, 2)
            print(f"✅ User {inviter_id} heeft iemand uitgenodigd. Teller: {user_progress[inviter_id]}")
            send_progress(context.updater, inviter_id)

# === Start Telegram bot in aparte thread ===
def start_bot():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(ChatMemberHandler(welcome, ChatMemberHandler.CHAT_MEMBER))
    dp.add_handler(ChatMemberHandler(track_invite, ChatMemberHandler.CHAT_MEMBER))
    updater.start_polling()
    print("🚀 Telegram bot gestart")
    updater.idle()

# === FastAPI webserver ===
app = FastAPI()

@app.get("/")
def root():
    return {"status": "Bot running"}

# Start bot in achtergrondthread bij webserver start
threading.Thread(target=start_bot, daemon=True).start()

# === Entry point voor uvicorn ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot:app", host="0.0.0.0", port=PORT, log_level="info")
