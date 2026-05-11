"""Flask application configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration."""
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://localhost/wucupid')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,      # Reconnect if DB dropped
        "pool_recycle": 280,        # Avoid idle SSL timeouts (Render kills around 300s)
        "pool_size": 2,             # Reduced from 5 to 2
        "max_overflow": 1,          # Reduced from 10 to 1
        "pool_timeout": 30,         # Timeout for getting a connection from the pool
        "connect_args": {
            "sslmode": "require",   # Force SSL
            "keepalives": 1,        # Enable keepalives
            "keepalives_idle": 30,  # Idle time before sending keepalive
            "keepalives_interval": 10,  # Time between keepalives
            "keepalives_count": 5,  # Number of keepalives before giving up
            "connect_timeout": 10,  # Connection timeout in seconds
            "options": "-c statement_timeout=60000",  # 60 second query timeout
            "application_name": "wucupid-web"  # Added for better monitoring
        }
    }
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    
    # Email
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@wucupid.com')
    
    # Frontend
    FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # Debug and Error Handling
    PROPAGATE_EXCEPTIONS = True
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() in ['true', 'on', '1'] 