import os
from datetime import timedelta

class Config:
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:postgres@localhost:5432/postgres"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "hire-lens-session-secret-key-minimum-32-bytes")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "hire-lens-jwt-secret-key-minimum-32-bytes")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)

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


