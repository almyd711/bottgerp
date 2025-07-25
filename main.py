import logging
import os
import random
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ✅ إعدادات البيئة
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6964741705"))
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# ✅ إعداد السجل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ لوحة أزرار رئيسية
def main_menu():
    keyboard = [
        [InlineKeyboardButton("💹 توصية جديدة", callback_data="get_signal")],
        [InlineKeyboardButton("🧠 تعلم التحليل", callback_data="learn")],
        [InlineKeyboardButton("📜 حول البوت", callback_data="about")],
        [InlineKeyboardButton("🎁 شارك البوت", callback_data="share")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ✅ أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 أهلاً {user.first_name}،\n"
        "هذا بوت توصيات تداول وتحليل ذكي.\n"
        "اختر من القائمة أدناه:",
        reply_markup=main_menu()
    )

# ✅ رد على الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "get_signal":
        await query.edit_message_text("📊 جاري تحليل السوق وإرسال التوصية...")
        await send_signal(query.message.chat_id)
    elif query.data == "learn":
        await query.edit_message_text("📘 تعلم التحليل:\n- EMA\n- RSI\n- Bollinger Bands\n- MACD\n...")
    elif query.data == "about":
        await query.edit_message_text("🤖 هذا البوت مقدم من المطور مجدي.\nللدعم: @your_support")
    elif query.data == "share":
        await query.edit_message_text("🔗 شارك البوت مع أصدقائك: t.me/YourBotUsername")

# ✅ دالة التوصيات (تجريبية)
async def send_signal(chat_id):
    from telegram import Bot
    bot = Bot(BOT_TOKEN)

    fake_time = datetime.now().strftime("%I:%M %p")
    signal_text = f"""
📊 التوصية: شراء (CALL)
💱 الزوج: EUR/USD OTC
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
⏰ التوقيت: {fake_time}
"""
    await bot.send_message(chat_id=chat_id, text=signal_text)

# ✅ بدء التشغيل
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    import asyncio
    asyncio.run(app.run_polling())
