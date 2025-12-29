from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
jwt = JWTManager()

def create_app(config_name='default'):
    """Application factory pattern."""
    app = Flask(__name__, 
                template_folder='../../frontend/html',
                static_folder='../../frontend')
    app.config.from_object(config[config_name])
    
    # JWT Configuration
    app.config['JWT_SECRET_KEY'] = app.config['SECRET_KEY']
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600  # 1 hour
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 2592000  # 30 days
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    jwt.init_app(app)
    CORS(app, origins=['http://localhost:3000', 'http://127.0.0.1:3000', 'http://127.0.0.1:5500', 'http://localhost:5500'])  # Allow frontend
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register API blueprint
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register other blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.volunteer import bp as volunteer_bp
    app.register_blueprint(volunteer_bp, url_prefix='/volunteer')
    
    from app.authority import bp as authority_bp
    app.register_blueprint(authority_bp, url_prefix='/authority')
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    return app

# Import models to ensure they are registered with SQLAlchemy
from app import models