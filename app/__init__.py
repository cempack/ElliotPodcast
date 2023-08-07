# app/__init__.py

from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = '613ca18acf1a6f84ece6bdd5a19980feafe8754a3a49f278395931bbea30062a'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    # Enable cookie-based session persistence
    app.config['REMEMBER_COOKIE_NAME'] = 'Steraudio'
    app.config['REMEMBER_COOKIE_DURATION'] = 3600 * 24 * 365  # One year

    from app.main.routes import main
    app.register_blueprint(main)

    from app.models import User, Podcast

    with app.app_context():
        db.create_all()

    return app
