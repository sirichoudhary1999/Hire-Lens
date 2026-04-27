from app.extensions import db

# Import all models here so SQLAlchemy can detect them
from .user import User
from .experience import Experience
from .academics import Academics
from .skills import Skills

__all__ = ["db", "User", "Experience", "Academics", "Skills"]
