import os

# Настройки SMTP (замени на реальные данные перед запуском)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USER = os.getenv("SMTP_USER", "your_email@example.com")
SMTP_PASS = os.getenv("SMTP_PASS", "your_smtp_password")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "your_email@example.com")

# Рандомные паузы в секундах между письмами (антибан)
DELAY_MIN = 15
DELAY_MAX = 35
