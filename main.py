from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import requests
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")  # ضع توكن البوت في متغير البيئة
SERVER_BASE = os.environ.get("SERVER_BASE", "http://localhost:8000")  # رابط السيرفر

def start(update: Update, context: CallbackContext):
    update.message.reply_text("مرحبًا! استخدم /addfeed <رابط قناة> لإضافة feed.")

def addfeed(update: Update, context: CallbackContext):
    if not context.args:
        update.message.reply_text("أرسل رابط القناة بعد الأمر.")
        return
    src = context.args[0]
    try:
        r = requests.post(f"{SERVER_BASE}/api/feeds", json={
            "source": src,
            "owner": update.effective_user.id
        }, timeout=15)
        if r.status_code == 201:
            data = r.json()
            update.message.reply_text(f"Feed تم إنشاؤه: {SERVER_BASE}/rss/{data['slug']}.xml")
        else:
            update.message.reply_text(f"خطأ: {r.text}")
    except Exception as e:
        update.message.reply_text(f"خطأ في الاتصال بالسيرفر: {e}")

def listfeeds(update: Update, context: CallbackContext):
    try:
        r = requests.get(f"{SERVER_BASE}/api/feeds?owner={update.effective_user.id}", timeout=15)
        feeds = r.json()
        if not feeds:
            update.message.reply_text("لا توجد feeds")
            return
        text = "\n".join([f"{f['id']}: {f['source']} -> /rss/{f['slug']}.xml" for f in feeds])
        update.message.reply_text(text)
    except Exception as e:
        update.message.reply_text(f"خطأ في الاتصال بالسيرفر: {e}")

def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('addfeed', addfeed))
    dp.add_handler(CommandHandler('listfeeds', listfeeds))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
