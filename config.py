import os
import dotenv

dotenv.load_dotenv()
# Model configuration
DEFAULT_MODEL = os.getenv("LLM_MODEL")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, os.getenv("HISTORY_FILE_NAME"))

# System Prompts
DEFAULT_SYSTEM_PROMPT = os.getenv("DEFAULT_SYSTEM_PROMPT")
