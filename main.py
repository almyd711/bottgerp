# ✅ بوت توصيات تداول شامل - باستخدام متغيرات البيئة

import os
import logging
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
)

# ✅ الإعدادات
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
IMAGE_URL = "https://yourdomain.com/logo.jpg"  # رابط صورة البوت

AUTHORIZED_USERS = set([ADMIN_ID])
PENDING_USERS = {}

# ✅ تفعيل اللوج
logging.basicConfig(level=logging.INFO)

# ✅ شاشة البدء
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    full_name = update.effective_user.full_name

    if user_id not in AUTHORIZED_USERS:
        if user_id in PENDING_USERS:
            await update.message.reply_text("⏳ طلبك قيد المراجعة. الرجاء الانتظار.")
        else:
            PENDING_USERS[user_id] = full_name
            keyboard = [
                [
                    InlineKeyboardButton("✅ قبول", callback_data=f"accept_{user_id}"),
                    InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user_id}")
                ]
            ]
            markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🆕 طلب دخول جديد:\n👤 الاسم: {full_name}\n🆔 ID: {user_id}",
                reply_markup=markup
            )
            await update.message.reply_text("🛑 البوت خاص. تم إرسال طلبك للمطور.")
        return

    await send_main_menu(update, context)

# ✅ إرسال القائمة الرئيسية
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 EUR/USD OTC", callback_data='pair_EUR/USD')],
        [InlineKeyboardButton("📘 تعلم التحليل", callback_data='learn')],
        [InlineKeyboardButton("📤 مشاركة التوصية", switch_inline_query="")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=IMAGE_URL,
        caption="👋 مرحبًا بك في بوت التوصيات 👇 اختر ما تريد:",
        reply_markup=reply_markup
    )

# ✅ أزرار القبول والرفض
async def manage_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("accept_"):
        uid = int(data.split("_")[1])
        AUTHORIZED_USERS.add(uid)
        PENDING_USERS.pop(uid, None)
        await context.bot.send_message(uid, "✅ تم قبولك! يمكنك الآن استخدام البوت.")
        await query.edit_message_text("تم قبول المستخدم.")
    elif data.startswith("reject_"):
        uid = int(data.split("_")[1])
        PENDING_USERS.pop(uid, None)
        await context.bot.send_message(uid, "❌ تم رفض طلبك. يمكنك إعادة الطلب لاحقًا.")
        await query.edit_message_text("تم رفض المستخدم.")

# ✅ التعامل مع الأزرار الرئيسية
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "learn":
        await query.edit_message_text("📘 تعلم التحليل:\n- EMA: المتوسطات المتحركة\n- RSI: مؤشر القوة النسبية\n- Bollinger: النطاقات السعرية\nالمزيد قريبًا...")
        return

    if data.startswith("pair_"):
        pair = data.split("_")[1]
        recommendation = await get_recommendation(pair)
        await query.edit_message_caption(caption=recommendation)

# ✅ توليد التوصية من المؤشرات (مثال ثابت)
async def get_recommendation(pair):
    time_now = datetime.now().strftime("%I:%M %p")
    return f"""📊 التوصية: شراء (CALL)
💱 الزوج: {pair} OTC
🔍 التحليل:
🔹 EMA:
- EMA20 = 1.0891
- EMA50 = 1.0782
📈 الاتجاه: صاعد ✅

🔸 RSI = 55.09
✅ منطقة تداول طبيعية

🔻 Bollinger Bands: أسفل الحد السفلي

📚 شرح المؤشرات:
- EMA20 > EMA50 → صعود
- RSI < 70 → غير مشبع
- Bollinger → يعطي احتمالات الانعكاس

⏱️ الفريم: 1 دقيقة
⏰ التوقيت: {time_now}."""

# ✅ تشغيل البوت
if __name__ == "__main__":
    if not BOT_TOKEN or not ADMIN_ID or not ALPHA_VANTAGE_API_KEY:
        raise Exception("❌ تأكد من إعداد المتغيرات: BOT_TOKEN و ADMIN_ID و ALPHA_VANTAGE_API_KEY")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(manage_requests, pattern="^(accept|reject)_"))
    app.add_handler(CallbackQueryHandler(handle_buttons, pattern="^(pair_|learn)"))
    app.run_polling()
