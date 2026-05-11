"""Flask application factory."""
import os
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_mail import Mail
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sqlalchemy import text
from flask_apscheduler import APScheduler
import logging, sys
import threading, time

# Import configuration from the new location
from .config.settings import Config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
scheduler = APScheduler()

# Global flag to control background threads
background_threads_active = True

def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # ---- make INFO logs actually show up ----
    gunicorn_err = logging.getLogger("gunicorn.error")
    handlers = gunicorn_err.handlers or [logging.StreamHandler(sys.stdout)]

    for h in handlers:
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    root = logging.getLogger()
    root.handlers = handlers
    root.setLevel(logging.INFO)

    app.logger.handlers = handlers
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False  # we already attached handlers
    # ----------------------------------------

    app.logger.info("APP_BOOT_INFO marker=should_appear")

    # Load configuration
    if test_config is None:
        app.config.from_object(Config)
    else:
        app.config.update(test_config)
    
    # Enforce strong SECRET_KEY in non-debug environments
    try:
        secret = app.config.get('SECRET_KEY')
        if not app.config.get('DEBUG', False):
            if not secret or secret == 'dev' or (isinstance(secret, str) and len(secret) < 16):
                raise RuntimeError('Insecure SECRET_KEY configuration')
    except Exception as e:
        # Fail fast for insecure configuration
        raise
    
    # Initialize Sentry if DSN is configured
    sentry_dsn = os.getenv('SENTRY_DSN')
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration()],
            traces_sample_rate=1.0
        )
    
    # Initialize extensions with proper CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "https://wucupid.com",
                "https://www.wucupid.com",
                "http://localhost:3000"
            ],
            "supports_credentials": True,
            "allow_headers": [
                "Content-Type",
                "X-CSRF-Token",
                "X-Requested-With",
                "baggage",
                "sentry-trace"
            ]
        }
    })
    db.init_app(app)
    # Import cleanup so its atexit handler registers
    from . import cleanup  # noqa: F401
    migrate.init_app(app, db)
    mail.init_app(app)
    
    # Configure and initialize APScheduler
    app.config['SCHEDULER_API_ENABLED'] = True
    scheduler.init_app(app)

    # Add teardown to ensure db sessions are removed
    @app.teardown_appcontext
    def cleanup(_exc=None):
        db.session.remove()
    
    # Add scheduled job for cycle tick
    @scheduler.task(
        'interval',
        id='cycle_tick',
        seconds=60,  # run every minute
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30  # grace time 
    )
    def scheduled_cycle_tick():
        with app.app_context():
            try:
                from .services.cycle_orchestrator import run_cycle_tick
                app.logger.info("cycle_tick_start")
                # Tag scheduler connections for observability
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text("SET application_name = 'wucupid-scheduler'"))
                except Exception:
                    pass
                run_cycle_tick()
                app.logger.info("cycle_tick_done")
            except Exception as e:
                app.logger.error(f"scheduled_cycle_tick_error: {e}")
            finally:
                db.session.remove()  # Ensure session cleanup after scheduler run
    
    # Start the scheduler
    scheduler.start()
    
    # Security headers
    @app.after_request
    def set_security_headers(response):
        # Basic hardening headers (tune CSP as needed for frontend assets)
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        response.headers.setdefault('Content-Security-Policy', "default-src 'self'")
        if not app.config.get('DEBUG', False):
            # 6 months HSTS
            response.headers.setdefault('Strict-Transport-Security', 'max-age=15552000; includeSubDomains; preload')
        return response

    # Add health check endpoint
    @app.route('/')
    def health_check():
        try:
            # Use SQLAlchemy text() for raw SQL
            with db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            app.logger.error(f"Health check failed: {e}")
            return jsonify({"status": "error", "detail": str(e)}), 500
    
    # Import and register blueprints
    from .routes.auth import auth as auth_blueprint
    from .routes.survey import survey as survey_blueprint
    from .routes.matches import matches_bp as matches_blueprint
    from .routes.cycle import cycle_bp as cycle_blueprint
    
    app.register_blueprint(auth_blueprint, url_prefix='/api/auth')
    app.register_blueprint(survey_blueprint, url_prefix='/api/survey')
    app.register_blueprint(matches_blueprint, url_prefix='/api/matches')
    app.register_blueprint(cycle_blueprint, url_prefix='/api/cycle')
    
    # Initialize cycle system
    with app.app_context():
        try:
            # Try to acquire the global cycle thread lock
            from .utils.locking import try_acquire_global_cycle_thread
            conn = try_acquire_global_cycle_thread()
            if conn:
                app.logger.info("cycle_global_lock_acquired")
                from .routes.cycle import init_cycle_system
                try:
                    init_cycle_system(app)
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
            else:
                app.logger.info("cycle_global_lock_held_elsewhere; skipping init")
        except Exception as e:
            app.logger.error(f"cycle_init_error err={e}")
    
    return app

def start_verification_monitor(app):
    """Start a background thread to monitor and fix auto-verification issues"""
    def verification_monitor():
        global background_threads_active
        app.logger.info("Starting verification monitor thread")
        
        while background_threads_active:
            try:
                with app.app_context():
                    # Check for users that have verification tokens but are marked as verified
                    # This is an inconsistent state that indicates auto-verification
                    from .models.models import User
                    auto_verified_users = User.query.filter(
                        User.verification_token.isnot(None),
                        User.is_email_verified.is_(True)
                    ).all()
                    
                    if auto_verified_users:
                        app.logger.error(f"VERIFICATION MONITOR: Found {len(auto_verified_users)} auto-verified users!")
                        
                        # Fix each user
                        for user in auto_verified_users:
                            tracking_id = f"monitor_{int(time.time())}_{user.email[:8]}"
                            app.logger.error(f"VERIFICATION MONITOR [{tracking_id}]: Fixing auto-verified user {user.email}")
                            
                            # Set back to unverified
                            user.is_email_verified = False
                            
                            # Log what happened
                            app.logger.info(f"VERIFICATION MONITOR [{tracking_id}]: Reset verification status for {user.email}")
                        
                        # Commit changes
                        db.session.commit()
                        app.logger.info("VERIFICATION MONITOR: Fixed all auto-verified users")
                    
                    # Also check for users created in last 24 hours that might have been auto-verified
                    from datetime import datetime, timedelta
                    recent_timeframe = datetime.utcnow() - timedelta(hours=24)
                    
                    recent_verified_users = User.query.filter(
                        User.created_at >= recent_timeframe,
                        User.verification_token.is_(None),
                        User.is_email_verified.is_(True)
                    ).all()
                    
                    # Log recently verified users for monitoring
                    if recent_verified_users:
                        app.logger.info(f"VERIFICATION MONITOR: {len(recent_verified_users)} users were verified in the last 24 hours")
            except Exception as e:
                try:
                    with app.app_context():
                        app.logger.error(f"VERIFICATION MONITOR: Error in monitor thread: {str(e)}")
                except:
                    # If we can't log with app_context, print to console
                    print(f"Error in verification monitor: {str(e)}")
            finally:
                try:
                    with app.app_context():
                        db.session.remove()
                except Exception:
                    pass
            
            # Sleep for a short time (5 seconds)
            time.sleep(5)
    
    # Start the monitor thread
    thread = threading.Thread(target=verification_monitor)
    thread.daemon = True
    thread.start()
