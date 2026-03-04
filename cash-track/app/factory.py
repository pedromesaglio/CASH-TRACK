"""
Application Factory
Creates and configures the Flask application
"""
from flask import Flask
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def create_app(config_name=None):
    """
    Application factory function
    Creates and configures the Flask application with all blueprints
    """
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')

    # Load configuration
    # Try FLASK_SECRET_KEY first (Railway-compatible), then SECRET_KEY, then fallback
    app.secret_key = os.getenv('FLASK_SECRET_KEY') or os.getenv('SECRET_KEY', 'dev-secret-key-change-this-in-production')

    # Security headers
    @app.after_request
    def set_security_headers(response):
        """Add security headers to all responses"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Only add HSTS in production with HTTPS
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # Session configuration
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    # Set SESSION_COOKIE_SECURE = True in production with HTTPS
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'

    # Upload configuration
    from app.utils.constants import UPLOAD_FOLDER, MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

    # Create upload folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # Initialize database
    from database import init_db
    init_db()

    # Register custom Jinja2 filters
    from app.utils.formatters import format_number
    app.template_filter('format_number')(format_number)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.expenses import expenses_bp
    from app.routes.income import income_bp
    from app.routes.investments import investments_bp
    from app.routes.binance import binance_bp
    from app.routes.admin import admin_bp
    from app.routes.ai import ai_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(income_bp)
    app.register_blueprint(investments_bp)
    app.register_blueprint(binance_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)

    return app
