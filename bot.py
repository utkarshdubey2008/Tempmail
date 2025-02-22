import os
import time
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

# Function to generate a new temporary email
def generate_temp_email(user_id):
    email = f"user{user_id}@tempmailbot.com"
    emails_collection.insert_one({
        "user_id": user_id,
        "email": email,
        "created_at": datetime.utcnow()
    })
    return email

# Function to delete expired emails
async def delete_expired_emails():
    now = datetime.utcnow()
    expired_emails = emails_collection.find({"created_at": {"$lt": now - timedelta(minutes=10)}})
    
    for email in expired_emails:
        bot.send_message(email["user_id"], f"🗑️ Your temporary email `{email['email']}` has expired! Generate a new one using `/new`.")
        emails_collection.delete_one({"_id": email["_id"]})

# Command: Start
@bot.on_message(filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    users_collection.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)
    
    await message.reply_text(
        "📩 **Welcome to Temp Mail Bot!**\n\nGenerate a temporary email with `/new`.\nUse `/stats` (Admin only) to check stats.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📧 Generate Email", callback_data="generate_email")]])
    )

# Command: Generate New Email
@bot.on_message(filters.command("new"))
async def new_email(client, message):
    user_id = message.from_user.id
    old_email = emails_collection.find_one({"user_id": user_id})
    
    if old_email:
        emails_collection.delete_one({"user_id": user_id})
    
    email = generate_temp_email(user_id)
    
    await message.reply_text(
        f"📨 **Your Temporary Email:** `{email}`\n(This will expire in 10 minutes.)",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email")]])
    )

# Command: Stats (Admin Only)
@bot.on_message(filters.command("stats") & filters.user(ADMIN_ID))
async def stats(client, message):
    total_users = users_collection.count_documents({})
    total_emails = emails_collection.count_documents({})
    
    await message.reply_text(
        f"📊 **Bot Statistics:**\n👤 Users: {total_users}\n📩 Emails Generated: {total_emails}"
    )

# Broadcast Function
@bot.on_message(filters.reply & filters.command("broadcast") & filters.user(ADMIN_ID))
async def broadcast(client, message):
    text = message.reply_to_message.text
    users = users_collection.find({})
    
    sent_count = 0
    for user in users:
        try:
            await bot.send_message(user["user_id"], text)
            sent_count += 1
        except:
            pass
    
    await message.reply_text(f"✅ Broadcast sent to {sent_count} users.")

# Handle Inline Button Clicks
@bot.on_callback_query()
async def button(client, callback_query):
    user_id = callback_query.from_user.id
    
    if callback_query.data == "generate_email":
        old_email = emails_collection.find_one({"user_id": user_id})
        if old_email:
            await callback_query.message.edit_text(f"📨 **Your Existing Email:** `{old_email['email']}`\n(This will expire in 10 minutes.)")
        else:
            email = generate_temp_email(user_id)
            await callback_query.message.edit_text(
                f"📨 **Your Temporary Email:** `{email}`\n(This will expire in 10 minutes.)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Delete Email", callback_data="delete_email")]])
            )

    elif callback_query.data == "delete_email":
        emails_collection.delete_one({"user_id": user_id})
        await callback_query.message.edit_text("✅ Email Deleted Successfully!")

# Scheduler for Auto Email Deletion
scheduler.add_job(delete_expired_emails, "interval", minutes=1)
scheduler.start()

# Run Bot
bot.run()
