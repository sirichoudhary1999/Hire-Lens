import os
from flask import Flask
from config import Config, validate_security_config
from app.extensions import db, jwt
from app.routes.user_routes import user_bp
from app.routes.profile_routes import skills_bp, experience_bp, academics_bp
from app.routes.job_application_routes import job_application_bp
from app.routes.resume_routes import resume_bp

from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    validate_security_config(app.config)

    CORS(
        app,
        resources={r"/*": {"origins": app.config["CORS_ALLOWED_ORIGINS"]}},
        allow_headers=app.config["CORS_ALLOW_HEADERS"],
        methods=app.config["CORS_ALLOW_METHODS"]
    )

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

    @app.route("/health")
    def health_check():
        return {"status": "ok"}, 200

    return app
