"""
config.py — Application configuration
Loads settings from .env file using python-dotenv.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Always load .env from the same directory as this file,
# regardless of the current working directory when flask is launched.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)


class Config:
    """Base configuration class."""

    # Flask secret key — MUST be changed in production
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # SQLAlchemy database URI
    _db_url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or "sqlite:///agenthire.db"
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File upload settings
    # Vercel has a read-only filesystem except for /tmp
    _upload_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
    if os.environ.get("VERCEL"):
        _upload_path = "/tmp"
    
    UPLOAD_FOLDER = _upload_path
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_EXTENSIONS = {"pdf"}

    # TinyFish API key
    TINYFISH_API_KEY = os.environ.get("TINYFISH_API_KEY", "")

    # SMTP Settings
    SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")

    # Ensure upload folder exists
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    except Exception:
        pass # In serverless environments, folders might be restricted


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


# Default to development
config = DevelopmentConfig()
