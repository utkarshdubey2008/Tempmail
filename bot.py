import telebot
import requests
import time
import threading
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "7758708579"))
MONGO_URI = os.getenv("MONGO_URI")

try:
    client = MongoClient(MONGO_URI)
    db = client["TempMailBot"]
    users_collection = db["users"]
    print("✅ Connected to MongoDB!")
except Exception as e:
    print(f"❌ MongoDB Connection Error: {e}")
    exit(1)

API_URL = "https://10minutemail.net/address.api.php"

bot = telebot.TeleBot(BOT_TOKEN)
notified_emails = {}

def get_user_email(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user.get("email") if user else None

def save_user_email(user_id, email):
    users_collection.update_one({"user_id": user_id}, {"$set": {"email": email}}, upsert=True)

def check_new_emails(user_id):
    email = get_user_email(user_id)
    if not email:
        return None
    
    try:
        response = requests.get(API_URL).json()
        mail_list = response.get("mail_list", [])

        if mail_list:
            latest_email = mail_list[0]
            return f"📩 *New Email Received!*\n\n📌 *Subject:* {latest_email['subject']}\n📧 *From:* {latest_email['from']}\n🔗 [View Email]({response['permalink']['url']})"
        else:
            return "❌ No new emails yet. Try again later."
    except Exception as e:
        print(f"❌ Email Fetch Error: {e}")
        return "❌ Error fetching emails. Please try again later."

@bot.message_handler(commands=["start"])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("📖 Docs", url="https://t.me/RagnarSpace"),
        InlineKeyboardButton("💬 Support", url="https://t.me/RagnarSpace"),
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
        response = requests.get(API_URL).json()
        
        if response.get("mail_get_mail"):
            email = response["mail_get_mail"]
            save_user_email(message.chat.id, email)
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔁 Refresh", callback_data="refresh_email"))
            markup.add(InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email"))

            bot.send_message(
                message.chat.id,
                f"✅ *New Temporary Email Created!*\n\n📧 *Your Email:* `{email}`\n🔗 [Check Inbox]({response['permalink']['url']})",
                parse_mode="Markdown",
                reply_markup=markup,
            )
        else:
            bot.send_message(message.chat.id, "❌ Failed to generate an email. Try again later.")
    except Exception as e:
        print(f"❌ Email Generation Error: {e}")
        bot.send_message(message.chat.id, "❌ Something went wrong. Please try again later.")

@bot.callback_query_handler(func=lambda call: call.data == "refresh_email")
def refresh_email(call):
    bot.answer_callback_query(call.id)
    email_status = check_new_emails(call.message.chat.id)
    bot.send_message(call.message.chat.id, email_status, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "delete_email")
def delete_email(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🗑️ *Your email has been deleted.*\n\nUse /new to generate a new one.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.reply_to_message and message.chat.id == OWNER_ID)
def broadcast(message):
    users = users_collection.find()
    success_count, failure_count = 0, 0

    for user in users:
        try:
            bot.copy_message(user["user_id"], OWNER_ID, message.message_id)
            success_count += 1
        except Exception as e:
            print(f"❌ Broadcast Error: {e}")
            failure_count += 1

    bot.send_message(OWNER_ID, f"📢 *Broadcast Sent!*\n✅ Successful: {success_count}\n❌ Failed: {failure_count}", parse_mode="Markdown")

print("✅ Bot is running...")
bot.polling()
