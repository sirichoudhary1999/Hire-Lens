from app.extensions import db

class ResumeOptimizationLog(db.Model):
    __tablename__ = "resume_optimization_logs"

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Job description input
    job_description = db.Column(db.Text, nullable=False)
    job_title = db.Column(db.String(200), nullable=True)

    # AI provider details
    ai_provider = db.Column(db.String(20), nullable=False)
    model_used = db.Column(db.String(50), nullable=True)

    # Results & metrics
    changes_made = db.Column(db.JSON, default=dict)
    tokens_used = db.Column(db.Integer, nullable=True)
    processing_time_ms = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(20), default='success')
    error_message = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "resume_id": self.resume_id,
            "user_id": self.user_id,
            "job_description": self.job_description,
            "job_title": self.job_title,
            "ai_provider": self.ai_provider,
            "model_used": self.model_used,
            "changes_made": self.changes_made,
            "tokens_used": self.tokens_used,
            "processing_time_ms": self.processing_time_ms,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
