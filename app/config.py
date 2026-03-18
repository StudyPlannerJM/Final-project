import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is not set!")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API Keys
    APYHUB_API_KEY = os.environ.get('APYHUB_API_KEY')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

    # Database
    _environment = os.environ.get('FLASK_ENV', 'development').lower()
    _database_url = os.environ.get('DATABASE_URL')
    if _environment == 'production' and not _database_url:
        raise ValueError(
            'DATABASE_URL environment variable is required in production'
        )
    if not _database_url:
        _database_url = 'sqlite:///braindump.db'
    # Render provides postgres:// but SQLAlchemy requires postgresql://
    if _database_url.startswith('postgres://'):
        _database_url = _database_url.replace(
            'postgres://',
            'postgresql://',
            1,
        )
    SQLALCHEMY_DATABASE_URI = _database_url
    if SQLALCHEMY_DATABASE_URI.startswith('sqlite'):
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_size': 2,
            'max_overflow': 1,
            'connect_args': {
                'connect_timeout': 10,
                'sslmode': 'require',
            },
        }

    # Session
    SESSION_COOKIE_NAME = 'braindump_session'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # OAuth/Google Calendar
    # For local development, use http://localhost:5000 or http://127.0.0.1:5000
    # For production, use your actual domain with https
    SERVER_URL = os.environ.get('SERVER_URL', 'http://localhost:5000')
    GOOGLE_OAUTH_REDIRECT_URI = os.environ.get(
        'GOOGLE_OAUTH_REDIRECT_URI',
        f"{SERVER_URL}/calendar/oauth2callback"
    )


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = False  # Set to True to see SQL queries


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
