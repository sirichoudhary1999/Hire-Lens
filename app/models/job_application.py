from app.extensions import db

class JobApplication(db.Model):
    __tablename__ = "job_applications"

    job_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="pending")
    notes = db.Column(db.Text, nullable=True)
    applied_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "company": self.company,
            "role": self.role,
            "status": self.status,
            "notes": self.notes,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None
        }
    