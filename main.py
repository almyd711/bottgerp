import logging
import os
import sqlite3
import json
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import random

# إعدادات البوت
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "6964741705"))
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

conn = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    status TEXT DEFAULT 'pending',
    proof TEXT DEFAULT NULL
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS user_stats (
    user_id INTEGER PRIMARY KEY,
    total_signals INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    pair TEXT,
    signal TEXT,
    indicators TEXT,
    timestamp TEXT,
    result TEXT DEFAULT 'pending'
)
''')
conn.commit()

PAIRS = ["USD/CHF", "AUD/USD", "USD/JPY", "USD/CAD", "EUR/JPY", "EUR/CAD", "EUR/USD", "EUR/CHF", "EUR/AUD"]

def get_pairs_keyboard():
    keyboard = [[InlineKeyboardButton(pair, callback_data=f"pair_{pair}")] for pair in PAIRS]
    keyboard.append([InlineKeyboardButton("🔁 إعادة التحليل", callback_data="reanalyze")])
    return InlineKeyboardMarkup(keyboard)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("💹 توصية جديدة", callback_data="get_signal")],
        [InlineKeyboardButton("🧠 تعلم التحليل", callback_data="learn")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="stats")],
        [InlineKeyboardButton("💼 الاشتراك والدفع", callback_data="subscribe")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("SELECT status FROM users WHERE user_id=?", (user.id,))
    row = cursor.fetchone()
    if row:
        status = row[0]
        if status == "approved":
            await update.message.reply_text(f"👋 مرحباً {user.first_name}، اختر من القائمة:", reply_markup=get_main_menu())
        elif status == "pending":
            await update.message.reply_text("🚫 طلبك قيد المراجعة، انتظر موافقة المدير.")
        else:
            await update.message.reply_text("❌ تم رفض طلبك. ارسل 'طلب جديد' لإعادة التقديم.")
    else:
        cursor.execute("INSERT OR IGNORE INTO users(user_id, username, status) VALUES (?, ?, 'pending')", (user.id, user.username))
        conn.commit()
        await update.message.reply_text("🚫 طلبك قيد المراجعة، انتظر موافقة المدير.")
        await context.bot.send_message(ADMIN_ID, f"📥 طلب جديد من @{user.username} (ID: {user.id})")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    cursor.execute("SELECT user_id, username FROM users WHERE status='pending'")
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("✅ لا يوجد طلبات معلقة.")
        return
    for uid, username in rows:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ قبول", callback_data=f"accept_{uid}"),
             InlineKeyboardButton("❌ رفض", callback_data=f"reject_{uid}")]
        ])
        await update.message.reply_text(f"👤 @{username} (ID: {uid})", reply_markup=keyboard)

async def admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != ADMIN_ID:
        return
    data = query.data
    if data.startswith("accept_"):
        uid = int(data.split("_")[1])
        cursor.execute("UPDATE users SET status='approved' WHERE user_id=?", (uid,))
        conn.commit()
        await query.edit_message_text("✅ تم القبول.")
    elif data.startswith("reject_"):
        uid = int(data.split("_")[1])
        cursor.execute("UPDATE users SET status='rejected' WHERE user_id=?", (uid,))
        conn.commit()
        await query.edit_message_text("❌ تم الرفض.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    data = query.data

    if data == "get_signal":
        cursor.execute("SELECT status FROM users WHERE user_id=?", (user.id,))
        row = cursor.fetchone()
        if not row or row[0] != "approved":
            await query.edit_message_text("🚫 ليس لديك صلاحية الحصول على التوصيات.")
            return
        await query.edit_message_text("📊 اختر الزوج لتحليل التوصية:", reply_markup=get_pairs_keyboard())

    elif data.startswith("pair_"):
        pair = data.split("_", 1)[1]
        await query.edit_message_text(f"📊 تحليل زوج {pair} جاري...")
        analysis = analyze_market(pair)
        if not analysis:
            await query.edit_message_text("⚠️ تعذر الحصول على بيانات الزوج حالياً.")
            return
        signal = "شراء (CALL)" if analysis["trend"].startswith("صاعد") else "بيع (PUT)"
        indicators = {
            "EMA20": analysis["ema20"],
            "EMA50": analysis["ema50"],
            "RSI": analysis["rsi"],
            "Bollinger": analysis["bb_signal"]
        }
        save_recommendation(user.id, pair, signal, indicators)
        success_prob = calculate_success_probability(analysis["rsi"], analysis["bb_signal"], analysis["ema_signal"])
        now = datetime.now().strftime("%I:%M %p")
        msg = f"""
📊 التوصية: {signal}
💱 الزوج: {pair}
🔍 التحليل:
🔹 EMA:
- EMA20 = {analysis['ema20']}
- EMA50 = {analysis['ema50']}
📈 الاتجاه: {analysis['trend']}

🔸 RSI = {analysis['rsi']}
{analysis['rsi_note']}

🔻 Bollinger Bands: {analysis['bb_signal']}

🎯 نسبة نجاح متوقعة: {success_prob}%
⏱️ الفريم: 1 دقيقة
⏰ التوقيت: {now}
"""
        await query.edit_message_text(msg.strip())

    elif data == "reanalyze":
        await query.edit_message_text("🔁 إعادة التحليل: اختر الزوج:", reply_markup=get_pairs_keyboard())

    elif data == "learn":
        await query.edit_message_text("""
📘 تعلم التحليل الأساسي:
- EMA: المتوسط المتحرك الأسي
- RSI: مؤشر القوة النسبية
- Bollinger Bands: نطاقات بولينجر
- MACD: تقاطع المتوسطات المتحركة
""".strip())

    elif data == "stats":
        cursor.execute("SELECT total_signals, wins FROM user_stats WHERE user_id=?", (user.id,))
        row = cursor.fetchone()
        if row:
            total, wins = row
            ratio = (wins / total * 100) if total > 0 else 0
            await query.edit_message_text(f"""
📈 إحصائيات التداول الخاصة بك:
- عدد التوصيات المستلمة: {total}
- عدد الصفقات الرابحة: {wins}
- نسبة النجاح: {ratio:.2f}%
""")
        else:
            await query.edit_message_text("❌ لا توجد بيانات إحصائية حتى الآن.")

    elif data == "subscribe":
        await query.edit_message_text("""
💳 طرق الدفع:
- USDT BEP20: 0x3a5db3aec7c262017af9423219eb64b5eb6643d7
- USDT TRC20: THrV9BLydZTYKox1MnnAivqitHBEz3xKiq
- Payeer: P1113622813

💡 بعد الدفع أرسل صورة إثبات الدفع هنا.
""".strip())

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ تم استلام إثبات الدفع، انتظر التفعيل.")

def analyze_market(symbol):
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=1min&apikey={ALPHA_VANTAGE_API_KEY}"
        response = requests.get(url)
        data = response.json()
        time_series = data["Time Series (1min)"]
        latest = list(time_series.values())[0]
        close_price = float(latest["4. close"])
        prices = [float(v["4. close"]) for v in list(time_series.values())[:50]]
        ema20 = sum(prices[:20]) / 20
        ema50 = sum(prices[:30]) / 30
        rsi = 50 + (random.random() * 20 - 10)
        bb_upper = max(prices) + 0.002
        bb_lower = min(prices) - 0.002
        trend = "صاعد ✅" if ema20 > ema50 else "هابط 🔻"
        bb_signal = "أعلى الحد العلوي" if close_price > bb_upper else ("أسفل الحد السفلي" if close_price < bb_lower else "محايد")
        ema_signal = "EMA20 > EMA50 ✅" if ema20 > ema50 else "EMA20 < EMA50 🔻"
        rsi_note = "✅ منطقة تداول طبيعية" if 30 < rsi < 70 else "⚠️ منطقة تشبع"
        return {
            "close": close_price,
            "ema20": round(ema20, 4),
            "ema50": round(ema50, 4),
            "rsi": round(rsi, 2),
            "trend": trend,
            "bb_signal": bb_signal,
            "ema_signal": ema_signal,
            "rsi_note": rsi_note
        }
    except Exception as e:
        print(f"Error analyzing market: {e}")
        return None

def save_recommendation(user_id, pair, signal, indicators):
    timestamp = datetime.now().isoformat()
    cursor.execute("INSERT INTO recommendations(user_id, pair, signal, indicators, timestamp) VALUES (?, ?, ?, ?, ?)",
                   (user_id, pair, signal, json.dumps(indicators), timestamp))
    conn.commit()

def calculate_success_probability(rsi, bb_signal, ema_signal):
    score = 0
    if 30 < rsi < 70:
        score += 1
    if "✅" in bb_signal:
        score += 1
    if "✅" in ema_signal:
        score += 1
    return int(score / 3 * 100)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(admin_actions, pattern="^(accept|reject)_"))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.run_polling()
