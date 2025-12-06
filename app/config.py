import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-this-in-production")  # Важно!
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    WATCH_MEDIA = os.getenv("WATCH_MEDIA", "0") == "1"

    MEDIA_DIR = BASE_DIR / "static" / "media"
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-to-secure-key")