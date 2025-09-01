import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ChatInviteLink, Update
from telegram.ext import Application, ChatMemberHandler, ContextTypes

# === Load secrets from .env ===
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
PRIVATE_GROUP = os.getenv("PRIVATE_GROUP")

# === In-memory storage ===
user_progress = {}       # {user_id: int}
user_invite_links = {}   # {invite_link: inviter_id}


# === Helper: send progress message ===
async def send_progress_message(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    progress = user_progress.get(user_id, 0)

    if progress < 2:
        # zoek persoonlijke invite link van deze user
        link = next((l for l, inviter in user_invite_links.items() if inviter == user_id), None)

        keyboard = [[InlineKeyboardButton(f"Share to unlock ({progress}/2)", url=link)]]
        text = "Please share this channel with 2 friends to unlock the group:"
    else:
        keyboard = [[InlineKeyboardButton("Open de groep", url=PRIVATE_GROUP)]]
        text = "✅ Je hebt 2 vrienden toegevoegd! Klik hieronder voor toegang."

    await context.bot.send_message(
        chat_id=user_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# === New member joins channel → send personal link ===
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        user_id = member.new_chat_member.user.id

        # initialiseer progress
        if user_id not in user_progress:
            user_progress[user_id] = 0

            # maak persoonlijke invite link
            invite: ChatInviteLink = await context.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                creates_join_request=False,
                member_limit=0,
                name=f"invite_{user_id}"
            )
            user_invite_links[invite.invite_link] = user_id

        # stuur knop in privé
        try:
            await send_progress_message(context, user_id)
        except Exception as e:
            print(f"❌ Kon user {user_id} geen privébericht sturen: {e}")


# === Track invites ===
async def track_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        if member.invite_link and member.invite_link.invite_link in user_invite_links:
            inviter_id = user_invite_links[member.invite_link.invite_link]
            user_progress[inviter_id] = min(user_progress[inviter_id] + 1, 2)

            print(f"✅ User {inviter_id} heeft iemand uitgenodigd. Nieuwe teller: {user_progress[inviter_id]}")
            await send_progress_message(context, inviter_id)


# === Main ===
def main():
    app = Application.builder().token(TOKEN).build()

    # Events
    app.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(ChatMemberHandler(track_new_member, ChatMemberHandler.CHAT_MEMBER))

    print("🚀 Bot gestart en draait nu...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
