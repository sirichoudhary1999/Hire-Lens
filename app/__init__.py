import os
from flask import Flask
from config import Config
from app.extensions import db, jwt
from app.routes.user_routes import user_bp
from app.routes.profile_routes import skills_bp, experience_bp, academics_bp
from app.routes.job_application_routes import job_application_bp
from app.routes.resume_routes import resume_bp

from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    # Create upload directories
    os.makedirs(app.config['RESUME_FOLDER'], exist_ok=True)

    db.init_app(app)
    jwt.init_app(app)

    with app.app_context():
        db.create_all()

    app.register_blueprint(user_bp)
    app.register_blueprint(skills_bp)
    app.register_blueprint(experience_bp)
    app.register_blueprint(academics_bp)
    app.register_blueprint(job_application_bp)
    app.register_blueprint(resume_bp)

    return app
