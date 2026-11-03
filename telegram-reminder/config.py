import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").strip()
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()

TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow").strip()

# Настройки запроса к LLM
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "45"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "800"))

# Настройки распознавания речи (faster-whisper, локально и бесплатно)
# Модель: base (быстрее, ~145 МБ) или small (точнее, ~484 МБ)
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "ru")

# Папка для временных файлов (голосовые)
TEMP_DIR = os.getenv("TEMP_DIR", "temp")

DB_PATH = os.getenv("DB_PATH", "reminders.db").strip()