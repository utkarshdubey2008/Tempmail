import telebot
import os
import requests
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
import urllib3
from warnings import simplefilter

# Suppress InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
simplefilter('ignore', urllib3.exceptions.InsecureRequestWarning)

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

class TempMailAPI:
    """Class to interact with TempMail API."""

    BASE_URL = "https://www.emailnator.com/"

    def __init__(self):
        """Initialize the session and store the email."""
        session = self.getRequest()
        self.emailAddress = None
        if session:
            self.csrf = session.get("csrf")
            self.s = session.get("session")
            self.emailAddress = self.newEmail(["plusGmail", "dotGmail", "googleMail"])

    def getRequest(self):
        try:
            s = requests.Session()
            r = s.get(self.BASE_URL + "api", headers={"user-agent": "Mozilla/5.0", "accept": "*/*"}, verify=False)
            csrf = r.headers.get("set-cookie").split("=")[1].split(";")[0].replace("%3D", "=")
            return {"csrf": csrf, "session": s}
        except:
            return None

    def newEmail(self, types=["plusGmail", "dotGmail", "googleMail"]):
        try:
            r = self.s.post(self.BASE_URL + "generate-email", json={"email": types}, headers={
                "user-agent": "Mozilla/5.0",
                "x-xsrf-token": self.csrf,
                "content-type": "application/json",
                "x-requested-with": "XMLHttpRequest"
            }, verify=False)
            return r.json().get("email", [None])[0] if r.status_code == 200 else None
        except:
            return None

    def getEmailAddress(self) -> str:
        return self.emailAddress

    def getAllEmails(self) -> list:
        """Retrieve all received emails."""
        try:
            r = self.s.post(self.BASE_URL + "message-list", json={"email": self.emailAddress}, headers={
                "user-agent": "Mozilla/5.0",
                "x-xsrf-token": self.csrf,
                "content-type": "application/json",
                "x-requested-with": "XMLHttpRequest"
            }, verify=False)
            msgs = r.json().get("messageData")
            return msgs[1:6] if r.status_code == 200 and msgs else []
        except:
            return []

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
        mail = TempMailAPI()  # Create a new temp email
        email = mail.getEmailAddress()  # Get email address

        if not email:
            raise Exception("Failed to generate email")

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
        mail = TempMailAPI()
        mail.emailAddress = user_email  # Use the stored user email
        messages = mail.getAllEmails()

        if messages:
            message_text = "\n\n".join(
                [f"📌 *Subject:* {msg['textSubject']}\n📧 *From:* {msg['textFrom']}\n✉️ *Body:* {msg.get('body', 'No preview available')}"
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
