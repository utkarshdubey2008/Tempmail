import telebot
import time
import os
import requests as rq
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# Load credentials from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "7758708579"))  # Ensure it's an integer
MONGO_URI = os.getenv("MONGO_URI")

# MongoDB Connection
try:
    client = MongoClient(MONGO_URI)
    db = client["TempMailBot"]
    users_collection = db["users"]
    trash_collection = db["trash"]
    print("✅ Connected to MongoDB!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")
    exit(1)  # Stop execution if DB connection fails

bot = telebot.TeleBot(BOT_TOKEN)


class Mails:
    """Class to interact with TempMail API."""

    BASE_URL = "https://tempmail.bjcoderx.workers.dev"

    def __init__(self):
        """Initialize the session and store the email."""
        response = rq.get(f"{self.BASE_URL}/gen")
        self.emailAddress = response.json().get("mail")

    def getEmailAddress(self) -> str:
        return self.emailAddress

    def getAllEmails(self) -> list:
        """Retrieve all received emails."""
        response = rq.get(f"{self.BASE_URL}/inbox/{self.emailAddress}")
        return response.json().get("messages")


# Fetch user email from the database
def get_user_email(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user.get("email") if user else None


# Save user email in the database
def save_user_email(user_id, email):
    users_collection.update_one({"user_id": user_id}, {"$set": {"email": email}}, upsert=True)


# Delete user email from the database
def delete_user_email(user_id):
    users_collection.delete_one({"user_id": user_id})


# Move email to trash in the database
def move_email_to_trash(email):
    trash_collection.insert_one(email)


@bot.message_handler(commands=["start"])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("📖 Docs", url="https://t.me/RagnarSpace"),
        InlineKeyboardButton("💬 Support", url="https://t.me/RagnarSpace"),
    )
    markup.add(
        InlineKeyboardButton("👨‍💻 Developer", url=f"tg://user?id={OWNER_ID}")
    )

    bot.send_message(
        message.chat.id,
        "👋 *Welcome to TempMail Bot!*\n\n📩 Generate temporary emails & receive messages instantly.\n\nClick `/new` to generate your email!",
        parse_mode="Markdown",
        reply_markup=markup,
    )


@bot.message_handler(commands=["new"])
def generate_email(message):
    try:
        mail = Mails()  # Create a new temp email
        email = mail.getEmailAddress()  # Get email address

        save_user_email(message.chat.id, email)

        # Send email details with "Refresh" and "Delete" buttons
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔄 Refresh Inbox", callback_data="refresh"),
            InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email")
        )

        bot.send_message(
            message.chat.id,
            f"✅ *New Temporary Email Created!*\n\n📧 *Your Email:* `{email}`",
            parse_mode="Markdown",
            reply_markup=markup,
        )
    except Exception as e:
        print(f"❌ Email Generation Error: {e}")
        bot.send_message(message.chat.id, "❌ Something went wrong. Please try again later.")


@bot.callback_query_handler(func=lambda call: call.data == "refresh")
def refresh_email(call):
    user_email = get_user_email(call.message.chat.id)
    if not user_email:
        bot.answer_callback_query(call.id, "❌ No email found! Generate one using /new.")
        return

    try:
        mail = Mails()
        mail.emailAddress = user_email  # Use the stored user email
        messages = mail.getAllEmails()

        if messages:
            message_text = "\n\n".join(
                [f"📌 *Subject:* {msg['subject']}\n📧 *From:* {msg['from']}\n✉️ *Preview:* {msg.get('preview', 'No preview available')}"
                 for msg in messages]
            )

            # Move emails to trash collection
            for msg in messages:
                move_email_to_trash(msg)

            bot.send_message(call.message.chat.id, f"📩 *New Emails Received!*\n\n{message_text}", parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, "📭 No new emails yet. Try again later.")
    except Exception as e:
        print(f"❌ Email Fetch Error: {e}")
        bot.answer_callback_query(call.id, "❌ Failed to refresh inbox.")


@bot.callback_query_handler(func=lambda call: call.data == "delete_email")
def delete_email(call):
    delete_user_email(call.message.chat.id)
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🗑️ *Your email has been deleted.*\n\nUse /new to generate a new one.",
                     parse_mode="Markdown")


print("✅ Bot is running...")
bot.polling()
