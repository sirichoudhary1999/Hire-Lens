from app.extensions import db

class Academics(db.Model):
    __tablename__ = "academics"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    degree = db.Column(db.String(120), nullable=False)
    institution = db.Column(db.String(120), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    cgpa_percentage = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
                "id": self.id,
                "user_id": self.user_id,
                "degree": self.degree,
                "institution": self.institution,
                "start_date": self.start_date,
                "end_date": self.end_date,
                "cgpa_percentage": self.cgpa_percentage

        }