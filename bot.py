import time
import requests
import telebot
import threading
import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

# Telegram Bot Token
BOT_TOKEN = "8017963270:AAF4yR4mUnQEKSKX7at2Vwb1zYYXIELixxo"  # Replace with your bot token
ADMIN_ID = "7758708579"  # Replace with your admin's Telegram ID

# MongoDB Connection
client = MongoClient("mongodb+srv://ragnar:jqQSlKYchqlwdHiu@cluster0.dtjsf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["TempMailBot"]
users_collection = db["users"]
emails_collection = db["emails"]
stats_collection = db["stats"]

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Temp Mail API Base URL
BASE_URL = "https://tempmail.bjcoderx.workers.dev"

# Function to update stats
def update_stat(field):
    stats_collection.update_one({}, {"$inc": {field: 1}}, upsert=True)

# Start command
@bot.message_handler(commands=["start"])
def start_message(message):
    user_id = message.chat.id
    if not users_collection.find_one({"user_id": user_id}):
        users_collection.insert_one({"user_id": user_id, "messages_sent": 0})
        update_stat("total_users")

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📧 Generate Email", callback_data="generate_email"))
    markup.add(InlineKeyboardButton("📊 Statistics", callback_data="stats"))
    markup.add(InlineKeyboardButton("🛠 Support", callback_data="support"))

    bot.send_photo(
        user_id,
        photo="https://i.imgur.com/EbXsyrC.png",
        caption="💌 **Welcome to Temp Mail Bot!**\n\n"
                "Generate disposable email addresses to use on websites, forums, and services "
                "without exposing your real email.\n\n"
                "Enjoy online privacy with our services! 🔒",
        parse_mode="Markdown",
        reply_markup=markup
    )

# Handle button clicks
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "generate_email":
        generate_email(call.message)
    elif call.data == "stats":
        send_stats(call.message)
    elif call.data == "support":
        bot.answer_callback_query(call.id, "🛠 Contact support at: @YourSupportUsername")

# Generate a new email
@bot.message_handler(commands=["new"])
def generate_email(message):
    user_id = message.chat.id

    # Delete old email if exists
    old_email = emails_collection.find_one({"user_id": user_id})
    if old_email:
        emails_collection.delete_one({"user_id": user_id})

    # Request new temp email
    response = requests.get(f"{BASE_URL}/gen").json()
    if response["status"] == "ok":
        email = response["mail"]
        expiration_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

        # Save to database
        emails_collection.insert_one({"user_id": user_id, "email": email, "expires_at": expiration_time})
        update_stat("total_emails_generated")

        # Inline delete button
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🗑 Delete Email", callback_data="delete_email"))

        bot.send_message(user_id, f"✅ **Your Temporary Email:**\n📧 `{email}`\n\n"
                                  "⚠️ This email will automatically expire in **10 minutes**.\n"
                                  "Use /new to generate a new one.", parse_mode="Markdown", reply_markup=markup)
    else:
        bot.send_message(user_id, "❌ Failed to generate email. Please try again later.")

# Delete email manually
@bot.callback_query_handler(func=lambda call: call.data == "delete_email")
def delete_email(call):
    user_id = call.message.chat.id
    emails_collection.delete_one({"user_id": user_id})
    bot.send_message(user_id, "🗑 **Your temporary email has been deleted.**", parse_mode="Markdown")

# Function to check inbox and forward emails
def check_inbox():
    while True:
        for email_data in emails_collection.find():
            user_id = email_data["user_id"]
            email = email_data["email"]

            response = requests.get(f"{BASE_URL}/inbox/{email}").json()
            if "messages" in response and response["messages"]:
                for msg in response["messages"]:
                    subject = msg.get("subject", "No Subject")
                    sender = msg.get("from", "Unknown Sender")
                    bot.send_message(user_id, f"📩 **New Email Received!**\n\n"
                                              f"📨 **From:** {sender}\n"
                                              f"✉️ **Subject:** {subject}", parse_mode="Markdown")
                response["messages"] = []
                update_stat("total_messages")

        time.sleep(10)

# Function to delete expired emails
def delete_expired_emails():
    while True:
        current_time = datetime.datetime.utcnow()
        expired_emails = emails_collection.find({"expires_at": {"$lte": current_time}})

        for email in expired_emails:
            user_id = email["user_id"]
            bot.send_message(user_id, "⏳ **Your temporary email has expired.**\nUse /new to generate a new one.", parse_mode="Markdown")
            emails_collection.delete_one({"_id": email["_id"]})

        time.sleep(60)

# /stats command
@bot.message_handler(commands=["stats"])
def send_stats(message):
    stats = stats_collection.find_one({})
    total_users = stats.get("total_users", 0)
    total_messages = stats.get("total_messages", 0)
    total_emails = stats.get("total_emails_generated", 0)

    bot.send_message(message.chat.id, f"📊 **Bot Statistics**\n\n"
                                      f"👥 **Total Users:** {total_users}\n"
                                      f"📩 **Total Messages Sent:** {total_messages}\n"
                                      f"📧 **Total Emails Generated:** {total_emails}", parse_mode="Markdown")

# Admin Broadcast
@bot.message_handler(commands=["broadcast"])
def broadcast_step1(message):
    if str(message.chat.id) == ADMIN_ID:
        bot.send_message(message.chat.id, "📢 **Reply to a message with** `/broadcast` **to send it to all users.**", parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.reply_to_message and message.text == "/broadcast")
def broadcast_step2(message):
    if str(message.chat.id) == ADMIN_ID:
        broadcast_message = message.reply_to_message
        users = users_collection.find()

        sent_count = 0
        for user in users:
            try:
                if broadcast_message.text:
                    bot.send_message(user["user_id"], broadcast_message.text)
                elif broadcast_message.photo:
                    bot.send_photo(user["user_id"], broadcast_message.photo[-1].file_id, caption=broadcast_message.caption)
                elif broadcast_message.video:
                    bot.send_video(user["user_id"], broadcast_message.video.file_id, caption=broadcast_message.caption)
                elif broadcast_message.document:
                    bot.send_document(user["user_id"], broadcast_message.document.file_id, caption=broadcast_message.caption)
                sent_count += 1
            except:
                pass

        bot.send_message(ADMIN_ID, f"✅ Broadcast sent to **{sent_count} users**.", parse_mode="Markdown")

# Start background threads
threading.Thread(target=check_inbox, daemon=True).start()
threading.Thread(target=delete_expired_emails, daemon=True).start()

# Start bot
bot.polling(non_stop=True)
