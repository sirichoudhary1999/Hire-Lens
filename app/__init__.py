from flask import Flask
from config import Config
from app.extensions import db, jwt
from app.routes import user_bp
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

    return app
