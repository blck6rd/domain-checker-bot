import os

# Telegram Bot Token - получить у @BotFather
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8295553004:AAHQX59PIewL3M5L_dTMlOFOqQnELcgqplo")

# Путь к файлу с доменами
DOMAINS_FILE = "domains.json"

# Порог предупреждения (дни до истечения)
EXPIRY_WARNING_DAYS = 31
