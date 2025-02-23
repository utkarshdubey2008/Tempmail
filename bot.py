import telebot
import requests
import time
import threading
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "7758708579"))  # Ensure it's an integer
MONGO_URI = os.getenv("MONGO_URI")


client = MongoClient(MONGO_URI)
db = client["TempMailBot"]
users_collection = db["users"]

# TempMail API Base URL
BASE_URL = "https://tempmail.bjcoderx.workers.dev"

bot = telebot.TeleBot(BOT_TOKEN)

notified_emails = {}


def get_user_email(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user["email"] if user else None


def save_user_email(user_id, email):
    users_collection.update_one({"user_id": user_id}, {"$set": {"email": email}}, upsert=True)

def check_new_emails():
    while True:
        users = users_collection.find()
        for user in users:
            email = user["email"]
            response = requests.get(f"{BASE_URL}/inbox/{email}").json()
            
            if response["status"] == "ok" and response.get("messages"):
                for msg in response["messages"]:
                    msg_id = msg["subject"] + msg["from"]
                    
                    
                    if msg_id not in notified_emails.get(user["user_id"], set()):
                        notified_emails.setdefault(user["user_id"], set()).add(msg_id)
                        
                        bot.send_message(
                            user["user_id"],
                            f"📩 *New Email Received!*\n\n📌 *Subject:* {msg['subject']}\n📧 *From:* {msg['from']}",
                            parse_mode="Markdown"
                        )
        time.sleep(10)  
        
threading.Thread(target=check_new_emails, daemon=True).start()

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

    bot.send_photo(
        message.chat.id,
        "https://telegra.ph/file/your-image.jpg",  # Replace with actual image
        caption="👋 *Welcome to TempMail Bot!*\n\n📩 Generate temporary emails & receive messages instantly.\n\nClick `/new` to generate your email!",
        parse_mode="Markdown",
        reply_markup=markup,
    )

@bot.message_handler(commands=["new"])
def generate_email(message):
    response = requests.get(f"{BASE_URL}/gen").json()
    
    if response["status"] == "ok":
        email = response["mail"]
        save_user_email(message.chat.id, email)
        
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email"))

        bot.send_message(
            message.chat.id,
            f"✅ *New Temporary Email Created!*\n\n📧 *Your Email:* `{email}`\n\n_Use this email to receive messages._",
            parse_mode="Markdown",
            reply_markup=markup,
        )
    else:
        bot.send_message(message.chat.id, "❌ Failed to generate an email. Try again later.")

@bot.callback_query_handler(func=lambda call: call.data == "delete_email")
def delete_email(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, "🗑️ *Your email has been deleted.*\n\nUse /new to generate a new one.", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.reply_to_message and message.chat.id == OWNER_ID)
def broadcast(message):
    users = users_collection.find()
    success_count = 0
    failure_count = 0

    for user in users:
        try:
            bot.copy_message(user["user_id"], OWNER_ID, message.message_id)
            success_count += 1
        except:
            failure_count += 1

    bot.send_message(OWNER_ID, f"📢 *Broadcast Sent!*\n✅ Successful: {success_count}\n❌ Failed: {failure_count}", parse_mode="Markdown")

print("Bot is running...")
bot.polling()
