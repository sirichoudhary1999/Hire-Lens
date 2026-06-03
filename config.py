import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _to_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(value):
    if not value:
        return []
    # Normalize origin values so "https://site.com/" and "https://site.com" both work.
    return [item.strip().rstrip("/") for item in str(value).split(",") if item.strip()]

class Config:
    ENV = os.getenv("FLASK_ENV", "production").lower()
    DEBUG = _to_bool(os.getenv("FLASK_DEBUG"), default=False)

    # Render provides DATABASE_URL starting with "postgres://"; SQLAlchemy requires "postgresql://"
    _db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres")
    SQLALCHEMY_DATABASE_URI = _db_url.replace("postgres://", "postgresql://", 1) if _db_url.startswith("postgres://") else _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _to_bool(os.getenv("SESSION_COOKIE_SECURE"), default=ENV == "production")
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_SECURE = _to_bool(os.getenv("JWT_COOKIE_SECURE"), default=ENV == "production")

    CORS_ALLOWED_ORIGINS = _parse_csv(
        os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    )
    CORS_ALLOW_HEADERS = ["Authorization", "Content-Type"]
    CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

    # File Upload Settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
    RESUME_FOLDER = os.path.join(UPLOAD_FOLDER, 'resumes')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = {'pdf', 'docx'}

    # AI Provider Settings
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    DEFAULT_AI_PROVIDER = os.getenv('DEFAULT_AI_PROVIDER', 'openai')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
    ANTHROPIC_MODEL = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
    AI_TIMEOUT_SECONDS = 60


def validate_security_config(config_obj):
    """Fail fast when required secrets are missing or weak."""
    required_secret_keys = ["SECRET_KEY", "JWT_SECRET_KEY"]

    for key in required_secret_keys:
        value = (config_obj.get(key) or "").strip()
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        if len(value) < 32:
            raise ValueError(f"{key} must be at least 32 characters long")

    cors_origins = config_obj.get("CORS_ALLOWED_ORIGINS") or []
    if config_obj.get("ENV") == "production" and not cors_origins:
        raise ValueError("CORS_ALLOWED_ORIGINS must be configured for production")


