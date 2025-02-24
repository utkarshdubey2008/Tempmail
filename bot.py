import telebot
import os
import time
from minutemail import Mail
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# Load credentials from environment variables
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Replace with your bot token
OWNER_ID = 7758708579  # Your Telegram ID
MONGO_URI = "YOUR_MONGODB_URI"  # Replace with your MongoDB URI

# MongoDB Connection
client = MongoClient(MONGO_URI)
db = client["TempMailBot"]
users_collection = db["users"]

bot = telebot.TeleBot(BOT_TOKEN)

def get_user_email(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user["email"] if user else None

def save_user_email(user_id, email):
    users_collection.update_one({"user_id": user_id}, {"$set": {"email": email}}, upsert=True)

@bot.message_handler(commands=["start"])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📖 Docs", url="https://t.me/RagnarSpace"),
        InlineKeyboardButton("💬 Support", url="https://t.me/RagnarSpace")
    )
    bot.send_message(
        message.chat.id,
        "👋 *Welcome to TempMail Bot!*\n\n📩 Generate temporary emails & receive messages instantly.\n\nClick `/new` to generate your email!",
        parse_mode="Markdown",
        reply_markup=markup,
    )

@bot.message_handler(commands=["new"])
def generate_email(message):
    mail = Mail()  # Generate a new email
    save_user_email(message.chat.id, mail.email)  # Store in database

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🔁 Refresh", callback_data="refresh_email"),
        InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email")
    )

    bot.send_message(
        message.chat.id,
        f"✅ *New Temporary Email Created!*\n\n📧 *Your Email:* `{mail.email}`",
        parse_mode="Markdown",
        reply_markup=markup,
    )

@bot.callback_query_handler(func=lambda call: call.data == "refresh_email")
def refresh_email(call):
    email = get_user_email(call.message.chat.id)
    if not email:
        bot.answer_callback_query(call.id, "❌ No email found. Use /new to generate one.")
        return

    mail = Mail(email)  # Use stored email
    messages = mail.fetch_message()  # Fetch emails

    if messages:
        emails_text = f"✅ *Temporary Email:* `{email}`\n\n📩 *Your Emails:*\n\n"
        for msg in messages:
            emails_text += f"📌 *Subject:* {msg['subject']}\n📧 *From:* {msg['sender']}\n🕒 *Received:* {msg['sentDateFormatted']}\n\n"

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔁 Refresh", callback_data="refresh_email"),
            InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email")
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=emails_text,
            parse_mode="Markdown",
            reply_markup=markup,
        )
    else:
        bot.answer_callback_query(call.id, "📭 No new emails yet.")

@bot.callback_query_handler(func=lambda call: call.data == "delete_email")
def delete_email(call):
    users_collection.delete_one({"user_id": call.message.chat.id})
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🗑️ *Your email has been deleted.*\n\nUse /new to generate a new one.", parse_mode="Markdown")

print("✅ Bot is running...")
bot.polling()
