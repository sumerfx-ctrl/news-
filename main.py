import asyncio
import re
import logging
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, ChatWriteForbiddenError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaWebPage

# -------------------- إعدادات --------------------
API_ID = 23935621
API_HASH = "5494a0d257f92563479b30909e53a4f7"
SESSION_STRING = "1ApWapzMBu16kF2YXUezNnd0DxLCLtbJJHKLsRByUeHlYvJyK5TLYAjGushTsvcHaixGWhSskkBGHmKfF52QfXEIE6QxP6AjbyHKvA20e9uyctRrt4dCiXnveNLy2Ua1Km1PX6hIb_bx9meQW9gJ9rATKf3TE0VJtvBzuuDkCAX1JPuAuzTQxm3cJk7pe-ROj6ZV4YDIJqffHjhWbM8ktuKhRpX_byVU068FMdhAlvtBtcVr7rs3sQZQ7UhPxB-aZCPTam5qu-RwFi1SGydUt_bzRSv6TdvdkZ1cheBqnfAvAqp6FdQ3OB4s0aaqqouD2fCwdscdT0GwIpFaJy5ZYdlVraVZ2B0g="

CHANNELS = {
    "https://t.me/SabrenNewss": ["@SuNew24", "@SuNew25", "@SuNew23"],
    "https://t.me/iraqi1_news": ["@SuNew24", "@SuNew25", "@SuNew23"],
    "https://t.me/inewschannel_tv": ["@SuNew24", "@SuNew25", "@SuNew23"],
    "https://t.me/dikharnews": ["@SuNew24", "@SuNew25", "@SuNew23"],
    "https://t.me/IraqMedicalStudents": ["@MedNews2"],
    "https://t.me/soi17": ["@MedNews2"],
    "https://t.me/AntiCryptoZ": ["@CourseBank0", "@Coinat0"],
    "https://t.me/Crypto_News95": ["@Coinat0", "@CourseBank0"],
    "https://t.me/QUICKECONEWS": ["@NewsFx24"],
    "https://t.me/fx_news_34": ["@NewsFx24"],
    "https://t.me/cryptocrunch": ["@Cryptonew29"],
    "https://t.me/CoingraphNews": ["@Cryptonew29"],
    "https://t.me/porter_news": ["@Cryptonew29"],
    "https://t.me/ArabicNewsNo": ["@sunew21"]
}

FORWARD_MODE = True  # استخدام forward مع إخفاء المصدر
ADD_SIGNATURE = False
SIGNATURE_TEXT = "🔁 أعيد النشر تلقائيًا"

REMOVE_TELEGRAM_LINKS = True
REMOVE_MENTIONS = True
REMOVE_ALL_LINKS = False
REPLACE_LINKS_WITH = ""
BLOCK_WORDS = ["تخفيضات", "سكسي", "اعلان", "صابرين"]

ADD_HEADER = True
HEADER_TEXT = ""
ADD_FOOTER = True
FOOTER_TEXT = ""

# -------------------- تسجيل --------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# -------------------- دالة الفلترة --------------------
def apply_filters(text):
    text = text or ""
    for word in BLOCK_WORDS:
        if word in text:
            return None

    if REMOVE_TELEGRAM_LINKS:
        text = re.sub(r"https?://t\.me/[^\s]+", "", text)
        text = re.sub(r"t\.me/[^\s]+", "", text)

    if REMOVE_MENTIONS:
        text = re.sub(r"@[A-Za-z0-9_]{4,32}", "", text)

    if REMOVE_ALL_LINKS:
        text = re.sub(r"https?://[^\s]+", REPLACE_LINKS_WITH, text)
        text = re.sub(r"www\.[^\s]+", REPLACE_LINKS_WITH, text)

    if ADD_HEADER:
        text = HEADER_TEXT + "\n" + text
    if ADD_FOOTER:
        text = text + FOOTER_TEXT

    return text.strip()

# -------------------- الدالة الرئيسية --------------------
async def main():
    if not SESSION_STRING:
        logger.error("⚠️ لم يتم إدخال Session String.")
        return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    try:
        await client.start()
        me = await client.get_me()
        logger.info(f"✅ تسجيل الدخول كـ {me.first_name} (@{me.username})")

        channel_entities = {}

        # ----- تحضير القنوات -----
        for source_link, target_usernames in CHANNELS.items():
            try:
                source_entity = await client.get_entity(source_link)
            except Exception:
                try:
                    await client(JoinChannelRequest(source_link))
                    await asyncio.sleep(2)
                    source_entity = await client.get_entity(source_link)
                except Exception as ex:
                    logger.error(f"❌ فشل الوصول إلى القناة {source_link}: {ex}")
                    continue

            target_entities = []
            for t in target_usernames:
                try:
                    target_entities.append(await client.get_entity(t))
                except Exception as e:
                    logger.error(f"⚠️ فشل الوصول إلى القناة الهدف {t}: {e}")

            if not target_entities:
                logger.warning(f"⚠️ لا توجد قنوات هدف صالحة لـ {source_link}")
                continue

            channel_entities[source_entity.id] = (source_entity, target_entities)

        if not channel_entities:
            logger.error("❌ لم يتم العثور على أي قناة مصدر صالحة.")
            await client.disconnect()
            return

        # ----- إنشاء معالجات الرسائل -----
        for src_id, (src, tgts) in channel_entities.items():
            @client.on(events.NewMessage(chats=[src.id]))
            async def handler(event, s=src, tlist=tgts):
                msg = event.message
                text = msg.message or msg.text or ""

                # -------- تسجيل وصول الرسالة قبل أي فلترة --------
                logger.info(f"🔔 وصلت رسالة جديدة من القناة {s.title} (ID: {msg.id})")

                filtered_text = apply_filters(text)

                if filtered_text is None:
                    logger.info(f"🚫 تم تجاهل منشور {msg.id} من {s.title} (كلمة ممنوعة).")
                    return

                for t in tlist:
                    try:
                        if FORWARD_MODE:
                            # تحويل الرسالة مع إخفاء المصدر
                            await client.send_message(t, filtered_text)
                            # يمكن إضافة دعم الميديا لاحقًا حسب الحاجة
                        else:
                            if msg.media:
                                await client.send_file(t, msg.media, caption=filtered_text)
                            else:
                                await client.send_message(t, filtered_text)

                        if ADD_SIGNATURE and filtered_text:
                            await client.send_message(t, SIGNATURE_TEXT)

                        logger.info(f"✅ تم إرسال المنشور من {s.title} إلى {t.title or t.id}")

                    except FloodWaitError as f:
                        logger.warning(f"⏳ FloodWaitError: الانتظار {f.seconds} ثانية")
                        await asyncio.sleep(f.seconds + 1)
                    except ChatWriteForbiddenError:
                        logger.error(f"🚫 لا يمكن الكتابة في القناة الهدف {t.title or t.id}")
                    except Exception as ex:
                        logger.exception(f"⚠️ خطأ عند إرسال منشور {msg.id}: {ex}")

        logger.info("🚀 البوت جاهز ويُراقب جميع القنوات الآن.")
        await client.run_until_disconnected()

    except Exception as e:
        logger.exception(f"❌ حدث خطأ غير متوقع أثناء التشغيل: {e}")
    finally:
        await client.disconnect()

# -------------------- تشغيل البرنامج --------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 تم الإيقاف يدويًا.")
    except Exception as e:
        logger.exception(f"❌ خطأ غير متوقع عند التشغيل: {e}")
