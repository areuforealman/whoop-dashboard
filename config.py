import os
from dotenv import load_dotenv

load_dotenv()

WHOOP_CLIENT_ID = os.environ["WHOOP_CLIENT_ID"]
WHOOP_CLIENT_SECRET = os.environ["WHOOP_CLIENT_SECRET"]
WHOOP_TOKEN_FILE = os.getenv("WHOOP_TOKEN_FILE", ".whoop_token.json")
WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_API_BASE = "https://api.prod.whoop.com/developer/v1"
WHOOP_REDIRECT_URI = "http://localhost:8000/auth/callback"
WHOOP_SCOPES = "read:recovery read:sleep read:workout read:cycles read:body_measurement offline"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

GCAL_TOKEN_FILE = os.getenv("GCAL_TOKEN_FILE", ".gcal_token.json")
GCAL_CREDENTIALS_FILE = os.getenv("GCAL_CREDENTIALS_FILE", "credentials.json")
GCAL_SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

DB_PATH = os.getenv("DB_PATH", "whoop.db")
PORT = int(os.getenv("PORT", 8000))
