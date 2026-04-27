from flask import Flask
from config import Config
from app.extensions import db, jwt
from app.routes.user_routes import user_bp
from app.routes.profile_routes import skills_bp, experience_bp, academics_bp
from app.routes.job_application_routes import job_application_bp

from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)

    with app.app_context():
        db.create_all()

    app.register_blueprint(user_bp)
    app.register_blueprint(skills_bp)
    app.register_blueprint(experience_bp)
    app.register_blueprint(academics_bp)
    app.register_blueprint(job_application_bp)

    return app
