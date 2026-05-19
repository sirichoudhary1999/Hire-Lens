from app.extensions import db

class Resume(db.Model):
    __tablename__ = "resumes"

    # Primary key & relationships
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Metadata
    title = db.Column(db.String(200), nullable=False, default="My Resume")
    is_primary = db.Column(db.Boolean, default=False)
    version = db.Column(db.Integer, default=1)

    # File information (optional, for uploaded files)
    original_filename = db.Column(db.String(255), nullable=True)
    file_path = db.Column(db.String(500), nullable=True)
    file_type = db.Column(db.String(10), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)

    # Structured resume data (JSON columns)
    personal_info = db.Column(db.JSON, default=dict)
    experiences = db.Column(db.JSON, default=list)
    education = db.Column(db.JSON, default=list)
    skills = db.Column(db.JSON, default=dict)
    projects = db.Column(db.JSON, default=list)
    certifications = db.Column(db.JSON, default=list)

    # AI optimization tracking
    last_optimized_at = db.Column(db.DateTime, nullable=True)
    optimization_count = db.Column(db.Integer, default=0)
    ai_provider_used = db.Column(db.String(20), nullable=True)

    # Version control
    parent_resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(),
                          onupdate=db.func.current_timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "is_primary": self.is_primary,
            "version": self.version,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "personal_info": self.personal_info if self.personal_info is not None else {},
            "experiences": self.experiences if self.experiences is not None else [],
            "education": self.education if self.education is not None else [],
            "skills": self.skills if self.skills is not None else {},
            "projects": self.projects if self.projects is not None else [],
            "certifications": self.certifications if self.certifications is not None else [],
            "last_optimized_at": self.last_optimized_at.isoformat() if self.last_optimized_at else None,
            "optimization_count": self.optimization_count,
            "ai_provider_used": self.ai_provider_used,
            "parent_resume_id": self.parent_resume_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
