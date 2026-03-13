"""
Flask Application Factory
Creates and configures the Flask application with all blueprints
"""
from flask import Flask
import os


def create_app(config_name=None):
    """
    Application Factory Pattern
    Creates and configures the Flask application
    """
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)

    # Load configuration
    if config_name == 'production':
        from config import ProductionConfig
        app.config.from_object(ProductionConfig)
    elif config_name == 'testing':
        from config import TestingConfig
        app.config.from_object(TestingConfig)
    else:
        from config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)

    # Initialize Firebase
    from app.utils.firebase_client import init_firebase
    init_firebase()

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.courses import courses_bp
    from app.routes.lessons import lessons_bp
    from app.routes.progress import progress_bp
    from app.routes.chatbot import chatbot_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(courses_bp, url_prefix='/courses')
    app.register_blueprint(lessons_bp, url_prefix='/lessons')
    app.register_blueprint(progress_bp, url_prefix='/progress')
    app.register_blueprint(chatbot_bp, url_prefix='/chatbot')

    # Error handlers - must be registered BEFORE blueprints
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import jsonify
        app.logger.error(f"404 Error: {error}")
        return jsonify({'error': 'Not Found', 'message': 'Trang không tồn tại'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import jsonify
        app.logger.error(f"500 Error: {error}")
        return jsonify({'error': 'Internal Server Error', 'message': 'Đã xảy ra lỗi server'}), 500

    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'EduLearn API'}

    # Inject Firebase Web config for auth pages and any template needing it
    @app.context_processor
    def inject_firebase_web_config():
        return {
            'firebase_web_config': {
                'apiKey': app.config.get('FIREBASE_WEB_API_KEY', ''),
                'authDomain': app.config.get('FIREBASE_WEB_AUTH_DOMAIN', ''),
                'projectId': app.config.get('FIREBASE_WEB_PROJECT_ID', ''),
                'storageBucket': app.config.get('FIREBASE_WEB_STORAGE_BUCKET', ''),
                'messagingSenderId': app.config.get('FIREBASE_WEB_MESSAGING_SENDER_ID', ''),
                'appId': app.config.get('FIREBASE_WEB_APP_ID', ''),
            }
        }

    return app
