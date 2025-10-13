import os
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

# Load environment variables from .env file
load_dotenv()

# Initialize SQLAlchemy without binding to an app yet
db = SQLAlchemy()


def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        "sqlite:///complete_study_planner.db"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions with the app
    db.init_app(app)
    # Blueprints will be registered here later

    return app