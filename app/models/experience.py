from app.extensions import db

class Experience(db.Model):
    __tablename__ = "experience"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    company = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)

def get_experience_by_user_id(user_id):
    return {
            "id": self.id,
            "company": self.company,
            "role": self.role,
            "start_date": self.start_date,
            "end_date": self.end_date
        }