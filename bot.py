import telebot
import requests
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

def get_user_email(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user.get("email") if user else None

def save_user_email(user_id, email, permalink):
    users_collection.update_one({"user_id": user_id}, {"$set": {"email": email, "permalink": permalink}}, upsert=True)

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
            permalink = response["permalink"]["url"]
            save_user_email(message.chat.id, email, permalink)

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("🔁 Refresh", callback_data="refresh_email"),
                InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email")
            )

            bot.send_message(
                message.chat.id,
                f"✅ *New Temporary Email Created!*\n\n📧 *Your Email:* `{email}`\n🔗 [Check Inbox]({permalink})",
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
    user = users_collection.find_one({"user_id": call.message.chat.id})
    if not user or "email" not in user:
        bot.answer_callback_query(call.id, "❌ No email found. Use /new to generate one.")
        return

    try:
        response = requests.get(API_URL).json()
        email = response.get("mail_get_mail")
        mail_list = response.get("mail_list", [])
        
        if not mail_list:
            bot.answer_callback_query(call.id, "📭 No new emails yet.")
            return

        emails_text = "📩 *Your Emails:*\n\n"
        for mail in mail_list:
            emails_text += f"📌 *Subject:* {mail['subject']}\n📧 *From:* {mail['from']}\n🕒 *Received:* {mail['datetime2']}\n🔗 [View Email]({response['permalink']['url']})\n\n"

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔁 Refresh", callback_data="refresh_email"),
            InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email")
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"✅ *Temporary Email:* `{email}`\n\n{emails_text}",
            parse_mode="Markdown",
            reply_markup=markup,
        )
    except Exception as e:
        print(f"❌ Email Refresh Error: {e}")
        bot.answer_callback_query(call.id, "❌ Error fetching emails. Try again later.")

@bot.callback_query_handler(func=lambda call: call.data == "delete_email")
def delete_email(call):
    bot.answer_callback_query(call.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    users_collection.delete_one({"user_id": call.message.chat.id})
    bot.send_message(call.message.chat.id, "🗑️ *Your email has been deleted.*\n\nUse /new to generate a new one.", parse_mode="Markdown")

print("✅ Bot is running...")
bot.polling()
