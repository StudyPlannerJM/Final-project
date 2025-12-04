import os
from flask import Flask
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate


# Load environment variables from .env file
load_dotenv()

# Initialize SQLAlchemy without binding to an app yet
db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # type: ignore[attr-defined]

migrate = Migrate()


def create_app():
    app = Flask(__name__)

    # Configuration
    secret_key = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev')
    app.config['SECRET_KEY'] = secret_key
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        "sqlite:///complete_study_planner.db"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Import blueprints here to avoid circular imports
    from app.routes import main as main_blueprint
    from app.auth import auth as auth_blueprint

    # Register blueprints
    app.register_blueprint(main_blueprint)
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    return app
