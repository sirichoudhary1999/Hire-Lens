from app.extensions import db

class Skills(db.Model):
    __table__name__ = "skills"

    id = db.Column(db.Integer, primary_key= True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    skill_name = db.Column(db.JSON, default=list)

    def get_skills(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "skill_name": self.skill_name
        }