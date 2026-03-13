import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration class"""
    SECRET_KEY = os.getenv("SECRET_KEY", "edulearn-dev-secret-key-change-in-production")
    FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")
    FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
    FIREBASE_STORAGE_BUCKET = os.getenv("FIREBASE_STORAGE_BUCKET")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Firebase Web SDK (for frontend Auth - lấy từ Firebase Console > Project Settings > General > Your apps)
    FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY", "AIzaSyAHeYMnEG_ZPGxxY20NRW69LET3vL2Ub24")
    FIREBASE_WEB_AUTH_DOMAIN = os.getenv("FIREBASE_WEB_AUTH_DOMAIN", "edulearn-c5fb5.firebaseapp.com")
    FIREBASE_WEB_PROJECT_ID = os.getenv("FIREBASE_WEB_PROJECT_ID", "edulearn-c5fb5")
    FIREBASE_WEB_STORAGE_BUCKET = os.getenv("FIREBASE_WEB_STORAGE_BUCKET", "edulearn-c5fb5.appspot.com")
    FIREBASE_WEB_MESSAGING_SENDER_ID = os.getenv("FIREBASE_WEB_MESSAGING_SENDER_ID", "1049258344326")
    FIREBASE_WEB_APP_ID = os.getenv("FIREBASE_WEB_APP_ID", "1:1049258344326:web:8992ae3fe9690d9158f607")
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB upload limit

    # Session configuration
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 86400 * 7


class DevelopmentConfig(Config):
    """Development environment configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production environment configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """Testing environment configuration"""
    DEBUG = True
    TESTING = True


config = {
    'development': 'config.DevelopmentConfig',
    'production': 'config.ProductionConfig',
    'testing': 'config.TestingConfig',
    'default': 'config.DevelopmentConfig'
}
