# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("API keys not found! Please check your .env file.")

# You can add other settings here, like template names
TEMPLATES = {
    "modern": "resume_bot/templates/modern.html",
    "creative": "resume_bot/templates/creative.html",
}
ACCENT_COLORS = ["#3498db", "#2ecc71", "#e74c3c", "#8e44ad"] # Blue, Green, Red, Purple
