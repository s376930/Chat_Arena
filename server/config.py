import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CONVERSATIONS_DIR = DATA_DIR / "conversations"

# Ensure directories exist
CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

# Data files
TOPICS_TASKS_FILE = DATA_DIR / "topics_tasks.json"
CONSENT_FILE = DATA_DIR / "consent.json"

# LLM configuration files
LLM_CONFIG_FILE = DATA_DIR / "llm_config.json"
PERSONAS_FILE = DATA_DIR / "personas.json"

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# OpenAI API key for Whisper fallback
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# API keys for LLM providers
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
XAI_API_KEY = os.getenv("XAI_API_KEY", "")

# Minimum characters required in "think" field before "speech" is enabled
MIN_THINK_CHARS = 10
