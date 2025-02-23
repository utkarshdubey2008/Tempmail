import telebot
import threading
import os
import time
from pymongo import MongoClient
from tempmail import EMail
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

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

bot = telebot.TeleBot(BOT_TOKEN)
notified_emails = {}

def get_user_email(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user["email"] if user else None

def save_user_email(user_id, email):
    users_collection.update_one({"user_id": user_id}, {"$set": {"email": email}}, upsert=True)

def delete_user_email(user_id):
    users_collection.delete_one({"user_id": user_id})

def check_new_emails():
    while True:
        users = users_collection.find()
        for user in users:
            email_address = user.get("email")
            if not email_address:
                continue

            try:
                email = EMail(email_address)
                inbox = email.get_inbox()

                for msg_info in inbox:
                    msg_id = msg_info.id

                    if msg_id not in notified_emails.get(user["user_id"], set()):
                        notified_emails.setdefault(user["user_id"], set()).add(msg_id)

                        bot.send_message(
                            user["user_id"],
                            f"📩 *New Email Received!*\n\n📌 *Subject:* {msg_info.subject}\n📧 *From:* {msg_info.from_addr}\n📜 *Message:* {msg_info.body}",
                            parse_mode="Markdown"
                        )
            except Exception as e:
                print(f"❌ Email Fetch Error: {e}")

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

    bot.send_message(
        message.chat.id,
        "👋 *Welcome to TempMail Bot!*\n\n📩 Generate temporary emails & receive messages instantly.\n\nClick `/new` to generate your email!",
        parse_mode="Markdown",
        reply_markup=markup,
    )

@bot.message_handler(commands=["new"])
def generate_email(message):
    try:
        email = EMail()
        save_user_email(message.chat.id, email.address)

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email"))

        bot.send_message(
            message.chat.id,
            f"✅ *New Temporary Email Created!*\n\n📧 *Your Email:* `{email.address}`",
            parse_mode="Markdown",
            reply_markup=markup,
        )
    except Exception as e:
        print(f"❌ Email Generation Error: {e}")
        bot.send_message(message.chat.id, "❌ Something went wrong. Please try again later.")

@bot.callback_query_handler(func=lambda call: call.data == "delete_email")
def delete_email(call):
    delete_user_email(call.message.chat.id)
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
        except Exception as e:
            print(f"❌ Broadcast Error: {e}")
            failure_count += 1

    bot.send_message(OWNER_ID, f"📢 *Broadcast Sent!*\n✅ Successful: {success_count}\n❌ Failed: {failure_count}", parse_mode="Markdown")

print("✅ Bot is running...")
bot.polling()
