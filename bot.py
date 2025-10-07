from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext
import requests, json

BOT_TOKEN = 'YOUR_BOT_TOKEN'
SERVER_BASE = 'https://your-server.example'  # حيث تخزن RSS وتدير Feeds

def start(update: Update, context: CallbackContext):
    update.message.reply_text("أرسل /addfeed <t.me/channel> لإضافة feed.")

def addfeed(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        update.message.reply_text("أرسل رابط القناة بعد الأمر.")
        return
    src = context.args[0]
    # إرسال طلب للسيرفر لإنشاء feed
    r = requests.post(f"{SERVER_BASE}/api/feeds", json={"source": src, "owner": update.effective_user.id})
    if r.status_code == 201:
        data = r.json()
        update.message.reply_text(f"Feed created: {SERVER_BASE}/rss/{data['slug']}.xml")
    else:
        update.message.reply_text(f"خطأ: {r.text}")

def listfeeds(update: Update, context: CallbackContext):
    r = requests.get(f"{SERVER_BASE}/api/feeds?owner={update.effective_user.id}")
    feeds = r.json()
    text = "\n".join([f"{f['id']}: {f['source']} -> /rss/{f['slug']}.xml" for f in feeds])
    update.message.reply_text(text or "لا توجد feeds")

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
