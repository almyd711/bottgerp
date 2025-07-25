import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# فقط مثال بدء تشغيل
print("🤖 Starting bot with:")
print("BOT_TOKEN:", BOT_TOKEN)
print("ADMIN_ID:", ADMIN_ID)
print("ALPHA_VANTAGE_API_KEY:", ALPHA_VANTAGE_API_KEY)
