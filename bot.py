import asyncio
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Bot Configuration
API_ID = 25482744
API_HASH = "e032d6e5c05a5d0bfe691480541d64f4"
BOT_TOKEN = "8017963270:AAF4yR4mUnQEKSKX7at2Vwb1zYYXIELixxo"
ADMIN_ID = 7758708579

# MongoDB Connection
MONGO_URI = "mongodb+srv://ragnar:jqQSlKYchqlwdHiu@cluster0.dtjsf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["temp_mail_bot"]
users_collection = db["users"]
emails_collection = db["emails"]

# Initialize Bot
bot = Client("temp_mail_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
scheduler = AsyncIOScheduler()

# Generate Unique Temporary Email
def generate_temp_email(user_id):
    email = f"user{user_id}@tempmailbot.com"
    emails_collection.update_one({"user_id": user_id}, {"$set": {"email": email, "created_at": datetime.utcnow()}}, upsert=True)
    return email

# Function to Delete Expired Emails
async def delete_expired_emails():
    now = datetime.utcnow()
    expired_emails = emails_collection.find({"created_at": {"$lt": now - timedelta(minutes=10)}})

    for email in expired_emails:
        bot.send_message(email["user_id"], f"🗑️ **Your temporary email `{email['email']}` has expired!**\nGenerate a new one using `/new`.")
        emails_collection.delete_one({"_id": email["_id"]})

# Start Command
@bot.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    users_collection.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

    await message.reply_text(
        "**📩 Welcome to Temp Mail Bot!**\n\n"
        "🔹 Generate a temporary email using `/new`\n"
        "🔹 Your email will expire in **10 minutes**\n"
        "🔹 Click the button below to generate an email now!\n\n"
        "**🔐 Safe & Secure Temp Mail Service**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📧 Generate Email", callback_data="generate_email")]
        ])
    )

# Generate New Email
@bot.on_message(filters.command("new"))
async def new_email(client, message):
    user_id = message.from_user.id
    existing_email = emails_collection.find_one({"user_id": user_id})

    # Delete old email if exists
    if existing_email:
        emails_collection.delete_one({"user_id": user_id})

    email = generate_temp_email(user_id)

    await message.reply_text(
        f"✅ **Temporary Email Generated!**\n\n"
        f"📨 **Email:** `{email}`\n"
        "🕒 **Expires in:** 10 minutes\n\n"
        "**🔹 You can delete this email anytime using the button below.**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email")]
        ])
    )

# Admin Stats Command
@bot.on_message(filters.command("stats") & filters.user(ADMIN_ID))
async def stats(client, message):
    total_users = users_collection.count_documents({})
    total_emails = emails_collection.count_documents({})

    await message.reply_text(
        "**📊 Bot Statistics**\n\n"
        f"👥 **Total Users:** {total_users}\n"
        f"📩 **Emails Generated:** {total_emails}\n\n"
        "**🔹 Admin Only Command**"
    )

# Broadcast Feature for Admin
@bot.on_message(filters.reply & filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast(client, message):
    broadcast_message = message.reply_to_message

    if not broadcast_message:
        await message.reply_text("❌ **Reply to a message with `/broadcast` to send it to all users.**")
        return

    users = users_collection.find({})
    sent_count = 0

    for user in users:
        try:
            await bot.send_message(user["user_id"], broadcast_message.text)
            sent_count += 1
        except:
            pass  # Ignore errors (e.g., user blocked bot)

    await message.reply_text(f"✅ **Broadcast sent to {sent_count} users.**")

# Handle Inline Button Clicks
@bot.on_callback_query()
async def button(client, callback_query):
    user_id = callback_query.from_user.id

    if callback_query.data == "generate_email":
        existing_email = emails_collection.find_one({"user_id": user_id})
        
        if existing_email:
            email = existing_email["email"]
        else:
            email = generate_temp_email(user_id)

        await callback_query.message.edit_text(
            f"📨 **Your Temporary Email:** `{email}`\n"
            "🕒 **Expires in:** 10 minutes\n\n"
            "🔹 Click below to delete your email.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email")]
            ])
        )

    elif callback_query.data == "delete_email":
        emails_collection.delete_one({"user_id": user_id})
        await callback_query.message.edit_text("✅ **Email Deleted Successfully!**")

# Scheduler for Auto Email Deletion
scheduler.add_job(delete_expired_emails, "interval", minutes=1)
scheduler.start()

# Run Bot
bot.run()
