import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from app.config import config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # type: ignore[attr-defined]
migrate = Migrate()


def create_app(config_name=None):
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app.config.from_object(config[config_name])

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Import blueprints here to avoid circular imports
    from app.auth import auth as auth_blueprint
    from app.routes import (
        main_bp,
        tasks_bp,
        flashcards_bp,
        pomodoro_bp,
        calendar_bp,
        summarizer_bp,
        ai_planner_bp
    )

    # Register blueprints
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(main_bp)  # No prefix - dashboard at /
    app.register_blueprint(tasks_bp)  # /tasks
    app.register_blueprint(flashcards_bp)  # /flashcards
    app.register_blueprint(pomodoro_bp)  # /pomodoro
    app.register_blueprint(calendar_bp)  # /calendar
    app.register_blueprint(summarizer_bp)  # /summarizer
    app.register_blueprint(ai_planner_bp)  # /ai-planner
    
    return app
