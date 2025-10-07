import os
import re
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# متغير البيئة BOT_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Please set BOT_TOKEN environment variable")

# قاعدة بيانات بسيطة للتجربة (يمكن استبدال SQLite لاحقًا)
FEEDS = {}

# --- أوامر البوت ---
def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "مرحبًا! استخدم /add <رابط قناة> لإضافة feed.\n"
        "استخدم /list لعرض القنوات."
    )

def add_feed(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("أرسل رابط القناة بعد الأمر.")
        return
    channel_url = context.args[0]
    feed_id = str(len(FEEDS) + 1)
    FEEDS[feed_id] = {
        "url": channel_url,
        "replacements": [],  # [{'pattern':'Bitcoin','replacement':'BTC'}]
        "blacklist": [],     # ['spam','forbidden']
        "header": "",
        "footer": "",
        "display_mode": "title_details"
    }
    update.message.reply_text(f"Feed تم إضافته: {channel_url} (ID: {feed_id})")

def list_feeds(update: Update, context: CallbackContext):
    if not FEEDS:
        update.message.reply_text("لا توجد feeds مضافة.")
        return
    text = "\n".join([f"{fid}: {f['url']}" for fid, f in FEEDS.items()])
    update.message.reply_text(text)

# --- إعداد البوت ---
def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", add_feed))
    dp.add_handler(CommandHandler("list", list_feeds))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
