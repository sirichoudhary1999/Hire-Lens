from app.extensions import db

# Import all models here so SQLAlchemy can detect them
from .user import User
from .experience import Experience
from .academics import Academics
from .skills import Skills
from .resume import Resume
from .resume_optimization_log import ResumeOptimizationLog

__all__ = ["db", "User", "Experience", "Academics", "Skills", "Resume", "ResumeOptimizationLog"]
