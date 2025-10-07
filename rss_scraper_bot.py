import feedparser
import re
import collections
from html import unescape, escape
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import nest_asyncio
import asyncio

# -------------------------------
# ⚠️⚠️⚠️ إعدادات مهمة لعميل المستخدم (User Client) ⚠️⚠️⚠️
# -------------------------------
# لكي يعمل سحب الأخبار من قنوات ليس لديك صلاحيات إدارية فيها، يجب استخدام
# مكتبة تعمل كـ "حساب مستخدم" مثل Pyrogram أو Telethon.
# هذا يتطلب إعدادات إضافية مثل API_ID و API_HASH وتسجيل دخول بحساب تيليجرام
# عادي (وليس حساب بوت).
# الأسطر التالية هي للتوضيح وستحتاج إلى استبدالها بإعدادات حقيقية وتثبيت Pyrogram/Telethon.
# -------------------------------
# API_ID = 1234567  # استبدل برقم API ID الخاص بك من my.telegram.org
# API_HASH = "YOUR_API_HASH"  # استبدل بـ API Hash الخاص بك
# from pyrogram import Client # افتراض استخدام Pyrogram

nest_asyncio.apply()
TELEGRAM_BOT_TOKEN = "7947964588:AAGS2ZXjrFUo96dS_-qIrFuLha8cfEBFcbI"
ADMIN_CHAT_ID = 5862954415
scheduler = AsyncIOScheduler()
bot = Bot(token=TELEGRAM_BOT_TOKEN)
is_scheduler_running = False

# -------------------------------
# 🌐 الأقسام (Sections) ديناميكي بالكامل
# -------------------------------
sections = {}
sent_entry_ids = {}  # لكل قسم سجل الأخبار المرسلة

# -------------------------------
# 🔍 استخراج الصورة من المقال (لـ RSS)
# -------------------------------
def extract_image(entry):
    if "media_content" in entry and len(entry.media_content) > 0:
        return entry.media_content[0].get("url")
    if "enclosures" in entry and len(entry.enclosures) > 0:
        return entry.enclosures[0].get("url")
    if "summary" in entry:
        # البحث عن صورة في محتوى HTML
        match = re.search(r'src=["\'](https?://\S+\.(jpg|jpeg|png|webp))["\']', entry.summary)
        if match:
            return match.group(1)
        # البحث عن رابط صورة مباشر في النص (التحقق من التعبير الأصلي)
        match = re.search(r'(https?://\S+\.(jpg|jpeg|png|webp))', entry.summary)
        if match:
            return match.group(1)
    return None

# -------------------------------
# 📤 وظيفة إرسال الخبر إلى التيليجرام (موحدة لـ RSS و Telegram Source)
# -------------------------------
async def post_to_channels(sec, title, summary, link, image_url, entry_id, section_key, test=False):
    """
    وظيفة موحدة لإرسال الخبر إلى جميع قنوات القسم.
    """
    new_posts = 0
    
    # لا ترسل إذا لم تكن في وضع التجربة والخبر مرسل مسبقاً
    if not test and entry_id in sent_entry_ids.get(section_key, []):
        return 0

    # تنظيف وتجهيز الرسالة
    title_clean = escape(re.sub(r'<.*?>', '', unescape(title)))
    summary_clean = escape(re.sub(r'<.*?>', '', unescape(summary)))
    
    # تحديد طريقة عرض الخبر
    details_mode = sec.get("details_mode", "title_text")
    if details_mode == "title":
        msg = f"📰 <b>{title_clean}</b>"
    elif details_mode == "text":
        msg = summary_clean
    else:
        msg = f"📰 <b>{title_clean}</b>\n\n{summary_clean}"

    # إضافة الرأس والهامش للقسم
    if sec.get("header"):
        msg = f"{sec['header']}\n\n{msg}"
    if sec.get("footer"):
        # إضافة رابط الخبر في نهاية الرسالة إذا كان موجوداً
        if link:
            msg += f"\n\n🔗 <a href='{link}'>قراءة المزيد</a>"
        msg += f"\n\n{sec['footer']}"
    elif link: # إذا لا يوجد هامش، فقط أضف رابط الخبر
        msg += f"\n\n🔗 <a href='{link}'>قراءة المزيد</a>"

    # الإرسال الفعلي
    for channel in sec["channels"]:
        try:
            if image_url:
                await bot.send_photo(chat_id=channel, photo=image_url, caption=msg, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=channel, text=msg, parse_mode="HTML", disable_web_page_preview=True)
            new_posts += 1
        except Exception as e:
            print(f"⚠️ خطأ في الإرسال إلى {channel}: {e}")

    # تسجيل الخبر المرسل
    if new_posts > 0 and entry_id:
        sent_entry_ids.setdefault(section_key, collections.deque(maxlen=100)).append(entry_id)
        
    return new_posts

# -------------------------------
# 📱 سحب الأخبار من قناة تيليجرام (يتطلب عميل مستخدم)
# -------------------------------
async def scrape_from_telegram_source(section_key, test=False):
    sec = sections.get(section_key)
    if not sec or not sec.get("source_channel"):
        return 0
    
    source_channel = sec["source_channel"]
    new_posts = 0

    # ⚠️⚠️⚠️ هذا هو الجزء الذي يتطلب مكتبة عميل مستخدم (مثل Pyrogram) ⚠️⚠️⚠️
    # لا يمكن تنفيذه بـ Bot API وحده. سيتم تمثيل المنطق بتعليقات.

    # try:
    #     # 1. إنشاء و بدء جلسة العميل (باستخدام Pyrogram كمثال)
    #     # client = Client("my_account", API_ID, API_HASH)
    #     # await client.start()

    #     # 2. جلب آخر 5 رسائل (أو 1 في وضع التجربة)
    #     # limit = 1 if test else 5
    #     # messages = [] # await client.get_history(source_channel, limit=limit)
        
    #     # 3. معالجة الرسائل
    #     # for message in reversed(messages): # يجب عكس الترتيب للإرسال من الأقدم للأحدث
    #     #     # التحقق من أن الرسالة تحتوي على محتوى نصي مهم (تجاهل الملصقات، الألعاب، إلخ)
    #     #     if not message.text and not message.caption:
    #     #         continue 

    #     #     # افتراض أن الرسالة هي خبر
    #     #     text_content = message.text or message.caption or ""
    #     #     
    #     #     # يمكنك استخدام طريقة أفضل لاستخراج العنوان والملخص إذا كان نمط القناة معروفًا
    #     #     # هنا، نستخدم أول 100 حرف كملخص والـ 30 حرف الأولى كعنوان
    #     #     summary = text_content
    #     #     title = summary.split('\n')[0][:30] + "..." if len(summary) > 30 else summary.split('\n')[0]
    #     #     
    #     #     # معرف فريد للرسالة لمنع الإرسال المتكرر
    #     #     entry_id = f"tg_{source_channel}_{message.id}"
            
    #     #     # استخراج رابط الصورة (إذا كانت الرسالة صورة)
    #     #     # image_url = None
    #     #     # إذا كانت الرسالة contain_photo أو video، يجب عليك تنزيلها ثم إعادة رفعها إلى Telegram
    #     #     # أو الحصول على رابط مباشر إذا كان ممكناً (وهو نادر في Telegram)

    #     #     # if message.photo:
    #     #     #    photo_file_id = message.photo.file_id
    #     #     #    # في هذه الحالة، يجب إرسال الصورة باستخدام file_id بدلاً من URL، 
    #     #     #    # أو تنزيلها وإعادة رفعها عبر Bot API إذا لم يكن البوت قادراً على استخدام file_id العميل

    #     #     # posts = await post_to_channels(sec, title, summary, message.link, image_url, entry_id, section_key, test)
    #     #     # new_posts += posts
            
    #     #     # if test and new_posts > 0:
    #     #     #     break

    # # except Exception as e:
    # #     print(f"⚠️ خطأ في سحب أخبار Telegram من {source_channel}: {e}")
    # # finally:
    # #     # 4. إغلاق الجلسة
    # #     # if 'client' in locals() and client:
    # #     #     await client.stop()
    
    # # -------------------------------------------------------------
    # # هذا الجزء فقط لتجربة الإرسال، يجب إزالته بعد تفعيل Pyrogram/Telethon
    # # -------------------------------------------------------------
    # if test:
        new_posts = await post_to_channels(sec, 
                                        "⚡️ خبر تجريبي من قناة تيليجرام", 
                                        f"تم سحب هذا الخبر من القناة المصدر **{source_channel}**. يجب عليك إعداد عميل المستخدم (مثل Pyrogram) لتفعيل السحب الحقيقي.", 
                                        "https://t.me/telegram", # رابط مثال
                                        None, 
                                        "test_tg_source_temp", 
                                        section_key, 
                                        test=True)
    
    return new_posts

# -------------------------------
# 📰 إرسال الأخبار لكل قسم
# -------------------------------
async def send_to_section(section_key, test=False):
    sec = sections.get(section_key)
    if not sec:
        return 0
    new_posts = 0

    # 1. معالجة روابط RSS أولاً
    if sec["rss_links"]:
        for link in sec["rss_links"]:
            try:
                feed = feedparser.parse(link)
                # في وضع التجربة نأخذ خبر واحد فقط، وإلا آخر 5
                entries = [feed.entries[0]] if test and feed.entries else reversed(feed.entries[:5])
                
                for entry in entries:
                    entry_id = entry.get('id', entry.link)
                    image_url = extract_image(entry)
                    
                    posts = await post_to_channels(
                        sec, 
                        entry.title, 
                        entry.summary if "summary" in entry else "", 
                        entry.link, 
                        image_url, 
                        entry_id, 
                        section_key, 
                        test
                    )
                    new_posts += posts
                    if test and new_posts > 0:
                        return new_posts # خبر واحد يكفي للتجربة

            except Exception as e:
                 print(f"⚠️ خطأ في معالجة RSS {link}: {e}")
    
    # 2. معالجة قناة المصدر في تيليجرام
    if sec.get("source_channel"):
        posts = await scrape_from_telegram_source(section_key, test)
        new_posts += posts
        if test and new_posts > 0:
            return new_posts # خبر واحد يكفي للتجربة
            
    return new_posts

async def send_to_all_sections():
    total_posts = 0
    for sec_key in sections.keys():
        total_posts += await send_to_section(sec_key)
    print(f"✅ تم إرسال {total_posts} خبر جديد عبر جميع الأقسام.")

# -------------------------------
# ⏰ جدولة النشر التلقائي
# -------------------------------
def schedule_job():
    global is_scheduler_running
    if not scheduler.get_jobs():
        # نستخدم lambda و asyncio.create_task لضمان أن الوظيفة async تعمل بشكل صحيح
        scheduler.add_job(lambda: asyncio.create_task(send_to_all_sections()), "interval", minutes=30)
        scheduler.start()
        is_scheduler_running = True

def stop_job():
    global is_scheduler_running
    scheduler.remove_all_jobs()
    is_scheduler_running = False

# -------------------------------
# 🔐 تحقق من المستخدم
# -------------------------------
def is_admin(update: Update):
    return update.effective_user.id == ADMIN_CHAT_ID

async def reject_access(update: Update):
    try:
        if update.message:
            await update.message.reply_text("❌ ليس لديك صلاحية لاستخدام هذا البوت.")
        elif update.callback_query:
            await update.callback_query.message.reply_text("❌ ليس لديك صلاحية لاستخدام هذا البوت.")
    except Exception as e:
        print(f"⚠️ خطأ في رفض الوصول: {e}")

# -------------------------------
# 🎛️ قوائم وأزرار (تحديث لإضافة زر مصدر القناة)
# -------------------------------
def main_menu():
    status_text = "✅ النشر فعال" if is_scheduler_running else "❌ النشر متوقف"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(status_text, callback_data="togglepost")],
        [InlineKeyboardButton("📚 إدارة الأقسام", callback_data="manage_sections")],
    ])

def sections_menu():
    buttons = []
    for key, sec in sections.items():
        buttons.append([InlineKeyboardButton(sec["name"], callback_data=f"section_{key}")])
    buttons.append([InlineKeyboardButton("➕ إضافة قسم جديد", callback_data="add_section")])
    buttons.append([InlineKeyboardButton("⬅️ العودة للقائمة الرئيسية", callback_data="mainmenu")])
    return InlineKeyboardMarkup(buttons)

def section_buttons(sec_key):
    sec = sections[sec_key]
    details_text = sec.get("details_mode", "title_text")
    details_display = {
        "title": "العنوان فقط",
        "text": "النص فقط",
        "title_text": "العنوان + النص"
    }.get(details_text, "العنوان + النص")
    
    # تحديد نص زر القناة المصدر
    source_channel_text = sec.get("source_channel")
    source_channel_button_text = f"📱 مصدر Telegram: {source_channel_text}" if source_channel_text else "➕ تعيين مصدر Telegram"

    buttons = [
        [InlineKeyboardButton("📚 إدارة مصادر RSS", callback_data=f"manage_feeds_{sec_key}"),
         InlineKeyboardButton("📢 إدارة قنوات النشر", callback_data=f"manage_channels_{sec_key}")],
        [InlineKeyboardButton(source_channel_button_text, callback_data=f"edit_source_channel_{sec_key}")], # الزر الجديد لمصدر التيليجرام
        [InlineKeyboardButton("📝 تعديل الهامش", callback_data=f"edit_footer_{sec_key}"),
         InlineKeyboardButton("📰 تعديل الرأس", callback_data=f"edit_header_{sec_key}")],
        [InlineKeyboardButton("✉️ إرسال رسالة للقنوات", callback_data=f"sendmessage_section_{sec_key}")],
        [InlineKeyboardButton(f"🔁 تبديل طريقة العرض ({details_display})", callback_data=f"toggle_details_{sec_key}")],
        [InlineKeyboardButton("🧪 تجربة إرسال خبر", callback_data=f"testpost_{sec_key}"),
         InlineKeyboardButton("❌ حذف القسم", callback_data=f"delete_section_{sec_key}")],
        [InlineKeyboardButton("⬅️ العودة للأقسام", callback_data="manage_sections")]
    ]
    return buttons

# -------------------------------
# 🔘 معالجة أزرار البوت (تحديث لإضافة زر مصدر القناة)
# -------------------------------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await reject_access(update)
    query = update.callback_query
    await query.answer()
    
    # ... (باقي الأزرار كما هي: mainmenu, manage_sections, togglepost) ...
    # القائمة الرئيسية
    if query.data == "mainmenu":
        await query.edit_message_text("🤖 القائمة الرئيسية:", reply_markup=main_menu())
        return
    elif query.data == "manage_sections":
        await query.edit_message_text("📚 الأقسام الحالية:", reply_markup=sections_menu())
        return
    
    # تبديل حالة النشر التلقائي
    elif query.data == "togglepost":
        global is_scheduler_running
        if is_scheduler_running:
            stop_job()
            msg = "❌ تم إيقاف النشر التلقائي."
        else:
            schedule_job()
            msg = "✅ تم تفعيل النشر التلقائي."
        await query.edit_message_text(f"🤖 القائمة الرئيسية:\n{msg}", reply_markup=main_menu())
        return

    elif query.data.startswith("section_"):
        sec_key = query.data[len("section_"):]
        if sec_key not in sections:
            await query.edit_message_text("⚠️ هذا القسم لم يعد موجودًا.", reply_markup=sections_menu())
            return
        sec = sections[sec_key]
        feeds_list = "\n".join(sec["rss_links"]) if sec["rss_links"] else "لا توجد مصادر RSS"
        channels_list = "\n".join(sec["channels"]) if sec["channels"] else "لا توجد قنوات نشر"
        source_channel = sec.get("source_channel") or "لم يتم تعيين قناة مصدر"
        msg = f"🗂️ قسم: {sec['name']}\n\n📢 قنوات النشر:\n`{channels_list}`\n\n📚 مصادر RSS:\n`{feeds_list}`\n\n📱 قناة المصدر Telegram:\n`{source_channel}`"
        await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(section_buttons(sec_key)), parse_mode="Markdown")
        return

    # إضافة قسم جديد
    elif query.data == "add_section":
        await query.edit_message_text("✏️ أرسل اسم القسم الجديد:", reply_markup=None)
        context.user_data["adding_section"] = True
        return

    # تجربة إرسال خبر واحد للقسم المحدد
    elif query.data.startswith("testpost_"):
        sec_key = query.data[len("testpost_"):]
        # تنبيه هام للمستخدم بخصوص الحاجة لإعداد Pyrogram/Telethon
        if not sections.get(sec_key, {}).get("rss_links") and sections.get(sec_key, {}).get("source_channel"):
             await query.answer("⚠️ تنبيه: السحب من Telegram يتطلب إعداد Pyrogram/Telethon أولاً. سيتم إرسال رسالة تجريبية.", show_alert=True)
             
        new_posts = await send_to_section(sec_key, test=True)
        if new_posts > 0:
            await query.edit_message_text("✅ تم إرسال خبر واحد للتجربة.", reply_markup=InlineKeyboardMarkup(section_buttons(sec_key)))
        else:
            await query.edit_message_text("⚠️ لم يتم العثور على أخبار للإرسال (المصادر فارغة/غير صالحة أو يلزم إعداد عميل المستخدم لسحب Telegram).", reply_markup=InlineKeyboardMarkup(section_buttons(sec_key)))
        return


    # تبديل طريقة عرض التفاصيل
    elif query.data.startswith("toggle_details_"):
        sec_key = query.data[len("toggle_details_"):]
        sec = sections[sec_key]
        current = sec.get("details_mode", "title_text")
        order = ["title_text", "title", "text"]
        sec["details_mode"] = order[(order.index(current)+1)%3]
        
        details_display = {
            "title": "العنوان فقط",
            "text": "النص فقط",
            "title_text": "العنوان + النص"
        }.get(sec["details_mode"], "العنوان + النص")
        
        await query.edit_message_text(f"🔁 تم تبديل عرض التفاصيل إلى: **{details_display}**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(section_buttons(sec_key)))
        return

    # إدارة المصادر
    elif query.data.startswith("manage_feeds_"):
        sec_key = query.data[len("manage_feeds_"):]
        context.user_data["editing_feeds"] = sec_key
        sec = sections[sec_key]
        feeds_list = "\n".join(sec["rss_links"]) if sec["rss_links"] else "لا توجد مصادر RSS"
        await query.edit_message_text(f"📚 مصادر RSS في {sec['name']}:\n`{feeds_list}`\n\n✏️ أرسل رابط RSS لإضافته أو الأمر `/delete <رابط>` للحذف. استخدم الأمر /cancel للإلغاء.", parse_mode="Markdown")
        return

    # إدارة القنوات
    elif query.data.startswith("manage_channels_"):
        sec_key = query.data[len("manage_channels_"):]
        context.user_data["editing_channels"] = sec_key
        sec = sections[sec_key]
        channels_list = "\n".join(sec["channels"]) if sec["channels"] else "لا توجد قنوات نشر"
        await query.edit_message_text(f"📢 قنوات النشر في {sec['name']}:\n`{channels_list}`\n\n✏️ أرسل معرف القناة (مثل `@channel_username` أو `-100...`) لإضافته أو الأمر `/delete <معرف>` للحذف. استخدم الأمر /cancel للإلغاء.", parse_mode="Markdown")
        return

    # 🆕 تعيين قناة مصدر Telegram
    elif query.data.startswith("edit_source_channel_"):
        sec_key = query.data[len("edit_source_channel_"):]
        context.user_data["editing_source_channel"] = sec_key
        sec = sections[sec_key]
        current_source = sec.get("source_channel") or "لم يتم تعيين قناة مصدر"
        await query.edit_message_text(f"📱 القناة المصدر الحالية في **{sec['name']}** هي: `{current_source}`\n\n✏️ أرسل معرف القناة الجديدة (مثل `@channel_username` أو `-100...`) التي تريد السحب منها. لإلغاء التعيين، أرسل `/clear`. استخدم الأمر /cancel للإلغاء.", parse_mode="Markdown")
        return

    # تعديل الهامش
    elif query.data.startswith("edit_footer_"):
        sec_key = query.data[len("edit_footer_"):]
        context.user_data["editing_footer"] = sec_key
        await query.edit_message_text("✏️ أرسل النص الذي تريد إضافته أو تعديله كهامش للقسم. (يمكنك استخدام ترميز HTML). استخدم الأمر /cancel للإلغاء.")
        return

    # تعديل الرأس
    elif query.data.startswith("edit_header_"):
        sec_key = query.data[len("edit_header_"):]
        context.user_data["editing_header"] = sec_key
        await query.edit_message_text("✏️ أرسل النص الذي تريد إضافته أو تعديله كرأس للقسم. (يمكنك استخدام ترميز HTML). استخدم الأمر /cancel للإلغاء.")
        return

    # إرسال رسالة للقنوات (الزر الجديد)
    elif query.data.startswith("sendmessage_section_"):
        sec_key = query.data[len("sendmessage_section_"):]
        sec = sections[sec_key]
        if not sec["channels"]:
             await query.edit_message_text(f"⚠️ قسم **{sec['name']}** لا يحتوي على قنوات لإرسال الرسالة إليها.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(section_buttons(sec_key)))
             return
        context.user_data["sending_message"] = sec_key
        await query.edit_message_text(f"✉️ أرسل الرسالة التي تريد إرسالها إلى قنوات قسم **{sec['name']}**. (يمكنك استخدام ترميز HTML). استخدم الأمر /cancel للإلغاء.", parse_mode="Markdown")
        return


    # حذف القسم
    elif query.data.startswith("delete_section_"):
        sec_key = query.data[len("delete_section_"):]
        if sec_key in sections:
            # رسالة تأكيد مبدئية
            await query.edit_message_text(
                f"هل أنت متأكد من حذف قسم **{sections[sec_key]['name']}**؟",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ تأكيد الحذف", callback_data=f"confirm_delete_{sec_key}")],
                    [InlineKeyboardButton("❌ إلغاء", callback_data="manage_sections")]
                ])
            )
        return

    # تأكيد حذف القسم
    elif query.data.startswith("confirm_delete_"):
        sec_key = query.data[len("confirm_delete_"):]
        if sec_key in sections:
            sections.pop(sec_key)
            sent_entry_ids.pop(sec_key, None)
        await query.edit_message_text("❌ تم حذف القسم بنجاح.", reply_markup=sections_menu())
        return

# -------------------------------
# 📝 معالجة الرسائل النصية (تحديث لإضافة مصدر القناة)
# -------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await reject_access(update)
    text = update.message.text.strip()

    # وظيفة مساعدة للعودة إلى قائمة القسم
    def get_back_button(sec_key):
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ العودة إلى القسم", callback_data=f"section_{sec_key}")]
        ])

    # إضافة قسم جديد
    if context.user_data.get("adding_section"):
        raw_name = text.strip()
        key = re.sub(r'\W+', '_', raw_name.lower())
        if not key:
            await update.message.reply_text("⚠️ اسم القسم غير صالح. حاول مرة أخرى.")
            return

        if key not in sections:
            sections[key] = {
                "name": raw_name, "channels": [], "rss_links": [], 
                "source_channel": None, # 🆕 المفتاح الجديد
                "footer": "", "header": "", "details_mode": "title_text"
            }
            sent_entry_ids[key] = collections.deque(maxlen=100)
        
        context.user_data.pop("adding_section", None)
        await update.message.reply_text(f"✅ تم إضافة القسم الجديد: **{raw_name}**", parse_mode="Markdown", reply_markup=sections_menu())
        return

    # 🆕 تعيين قناة مصدر Telegram
    if sec_key := context.user_data.get("editing_source_channel"):
        sec = sections[sec_key]
        if text.lower() == "/clear":
            sec["source_channel"] = None
            msg = "✅ تم إلغاء تعيين القناة المصدر Telegram."
        elif text:
            # التحقق البسيط من أن المعرف يبدو صالحًا كاسم مستخدم أو رقم
            if not (text.startswith('@') or text.startswith('-100') or text.isdigit()):
                 await update.message.reply_text("⚠️ المعرّف غير صالح. يجب أن يبدأ بـ `@` أو يكون بصيغة معرف رقمي مثل `-100...`.", reply_markup=get_back_button(sec_key))
                 return

            sec["source_channel"] = text
            msg = f"✅ تم تعيين القناة المصدر Telegram إلى: `{text}`"
            
        context.user_data.pop("editing_source_channel", None)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_back_button(sec_key))
        return

    # إرسال رسالة للقنوات
    if sec_key := context.user_data.get("sending_message"):
        sec = sections[sec_key]
        sent_count = 0
        for channel in sec["channels"]:
            try:
                # محاولة إرسال الرسالة باستخدام HTML
                await update.message.reply_copy(chat_id=channel, parse_mode="HTML")
                sent_count += 1
            except Exception as e:
                print(f"⚠️ خطأ في إرسال رسالة يدوية إلى {channel}: {e}")
        
        context.user_data.pop("sending_message", None)
        await update.message.reply_text(f"✅ تم إرسال رسالتك إلى **{sent_count}** قناة في قسم **{sec['name']}**.", parse_mode="Markdown", reply_markup=get_back_button(sec_key))
        return


    # تحرير الهامش
    if sec_key := context.user_data.get("editing_footer"):
        sections[sec_key]["footer"] = text
        context.user_data.pop("editing_footer", None)
        await update.message.reply_text(f"✅ تم حفظ الهامش للقسم:\n`{text}`", parse_mode="Markdown", reply_markup=get_back_button(sec_key))
        return

    # تحرير الرأس
    if sec_key := context.user_data.get("editing_header"):
        sections[sec_key]["header"] = text
        context.user_data.pop("editing_header", None)
        await update.message.reply_text(f"✅ تم حفظ الرأس للقسم:\n`{text}`", parse_mode="Markdown", reply_markup=get_back_button(sec_key))
        return

    # إدارة المصادر
    if sec_key := context.user_data.get("editing_feeds"):
        sec = sections[sec_key]
        if text.startswith("/delete "):
            link = text[8:].strip()
            if link in sec["rss_links"]:
                sec["rss_links"].remove(link)
                msg = "✅ تم حذف المصدر بنجاح."
            else:
                msg = "⚠️ المصدر غير موجود."
        else:
            if text and text not in sec["rss_links"]:
                sec["rss_links"].append(text)
                msg = "✅ تم إضافة المصدر بنجاح."
            else:
                msg = "⚠️ المصدر موجود بالفعل أو الرابط فارغ."

        context.user_data.pop("editing_feeds", None)
        await update.message.reply_text(msg, reply_markup=get_back_button(sec_key))
        return

    # إدارة القنوات
    if sec_key := context.user_data.get("editing_channels"):
        sec = sections[sec_key]
        if text.startswith("/delete "):
            ch = text[8:].strip()
            if ch in sec["channels"]:
                sec["channels"].remove(ch)
                msg = "✅ تم حذف القناة بنجاح."
            else:
                msg = "⚠️ القناة غير موجودة."
        else:
            if text and text not in sec["channels"]:
                # التحقق البسيط من أن المعرف يبدو صالحًا كاسم مستخدم أو رقم
                if not (text.startswith('@') or text.startswith('-100') or text.isdigit()):
                    await update.message.reply_text("⚠️ المعرّف غير صالح. يجب أن يبدأ بـ `@` أو يكون بصيغة معرف رقمي مثل `-100...`.", reply_markup=get_back_button(sec_key))
                    return
                
                sec["channels"].append(text)
                msg = "✅ تم إضافة القناة بنجاح."
            else:
                msg = "⚠️ القناة موجودة بالفعل أو المعرّف فارغ."

        context.user_data.pop("editing_channels", None)
        await update.message.reply_text(msg, reply_markup=get_back_button(sec_key))
        return

# -------------------------------
# ❌ معالجة أمر الإلغاء
# -------------------------------
async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء أي عملية تحرير أو إضافة قيد التنفيذ."""
    if not is_admin(update):
        return await reject_access(update)
    
    # قائمة بجميع المفاتيح التي تدل على عملية جارية
    editing_keys = [
        "adding_section", "editing_footer", "editing_header", 
        "editing_feeds", "editing_channels", "sending_message", 
        "editing_source_channel" # 🆕 المفتاح الجديد
    ]
    
    # تحديد القسم للعودة إليه
    sec_key_for_back = None
    for key in ["editing_footer", "editing_header", "editing_feeds", "editing_channels", "sending_message", "editing_source_channel"]:
        if context.user_data.get(key):
            sec_key_for_back = context.user_data[key]
            break

    # إزالة جميع مفاتيح العمليات الجارية
    for key in editing_keys:
        context.user_data.pop(key, None)

    if sec_key_for_back and sec_key_for_back in sections:
        # العودة إلى قائمة القسم إذا كنا في وضع التحرير لأحد الأقسام
        sec = sections[sec_key_for_back]
        feeds_list = "\n".join(sec.get("rss_links", [])) if sec.get("rss_links") else "لا توجد مصادر RSS"
        channels_list = "\n".join(sec.get("channels", [])) if sec.get("channels") else "لا توجد قنوات نشر"
        source_channel = sec.get("source_channel") or "لم يتم تعيين قناة مصدر"
        
        msg = f"✅ تم إلغاء العملية والعودة لقسم: **{sec.get('name', 'غير معروف')}**\n\n📢 قنوات النشر:\n`{channels_list}`\n\n📚 مصادر RSS:\n`{feeds_list}`\n\n📱 قناة المصدر Telegram:\n`{source_channel}`"
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(section_buttons(sec_key_for_back)))
    else:
        # العودة إلى قائمة الأقسام الرئيسية أو القائمة الرئيسية
        await update.message.reply_text("✅ تم إلغاء العملية.", reply_markup=sections_menu())


# -------------------------------
# ▶️ تشغيل البوت
# -------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await reject_access(update)
    # التأكد من جدولة الوظيفة عند بدء التشغيل لأول مرة
    if not scheduler.running:
        schedule_job()
    await update.message.reply_text("🤖 بوت الأخبار جاهز! استخدم الأزرار للتحكم 👇", reply_markup=main_menu())

# -------------------------------
# 🚀 التشغيل
# -------------------------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # معالجات الأوامر الرئيسية
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_action)) # إضافة معالج لأمر الإلغاء

    # معالجات الأزرار والرسائل
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ البوت يعمل الآن — اكتب /start في تيليجرام للتحكم (للمشرف فقط).")
    app.run_polling()
