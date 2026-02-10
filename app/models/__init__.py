from app.extensions import db

# Import all models here so SQLAlchemy can detect them
from .user import User

__all__ = ["db", "User"]
