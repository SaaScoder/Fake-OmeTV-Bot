import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ChatInviteLink
from telegram.ext import Application, ChatMemberHandler, ContextTypes

# .env laden
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
PRIVATE_GROUP = os.getenv("PRIVATE_GROUP")

# Opslag in RAM
user_progress = {}       # {user_id: int}
user_invite_links = {}   # {invite_link: inviter_id}

# Nieuwe user komt in kanaal
async def welcome_new_member(update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        user_id = member.new_chat_member.user.id

        if user_id not in user_progress:
            user_progress[user_id] = 0

            invite: ChatInviteLink = await context.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                creates_join_request=False,
                member_limit=0,
                name=f"invite_{user_id}"
            )
            user_invite_links[invite.invite_link] = user_id

        await send_progress_message(context, user_id)

# Update van teller & knop sturen
async def send_progress_message(context, user_id: int):
    progress = user_progress.get(user_id, 0)

    if progress < 2:
        link = next((l for l, inviter in user_invite_links.items() if inviter == user_id), None)
        keyboard = [[InlineKeyboardButton(f"Share to unlock ({progress}/2)", url=link)]]
        text = "Share this channel with 2 friends to unlock the group:"
    else:
        keyboard = [[InlineKeyboardButton("Open de groep", url=PRIVATE_GROUP)]]
        text = "✅ Je hebt 2 vrienden toegevoegd! Klik hieronder voor toegang."

    await context.bot.send_message(chat_id=user_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))

# Check wie invite gaf
async def track_new_member(update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        if member.invite_link and member.invite_link.invite_link in user_invite_links:
            inviter_id = user_invite_links[member.invite_link.invite_link]
            user_progress[inviter_id] = min(user_progress[inviter_id] + 1, 2)
            await send_progress_message(context, inviter_id)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(track_new_member, ChatMemberHandler.CHAT_MEMBER))
    app.run_polling()

if __name__ == "__main__":
    main()
