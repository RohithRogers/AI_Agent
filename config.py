import os
import dotenv

dotenv.load_dotenv()

# Model configuration
OFFLINE_MODE = os.getenv("LLM_MODEL")
ONLINE_MODE_GEMINI = os.environ.get("GOOGLE_API_KEY")
ONLINE_MODE_GROQ = os.environ.get("GROQ_API_KEY")


# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, os.getenv("HISTORY_FILE_NAME"))

# System Prompts
DEFAULT_SYSTEM_PROMPT = os.getenv("DEFAULT_SYSTEM_PROMPT")

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
