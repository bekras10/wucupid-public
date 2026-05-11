import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from .app import db
from .app.routes.auth import auth
from .app.routes.cycle import cycle_bp
from .app.routes.matches import matches_bp
from .app.routes.survey import survey
from .app.models.cycle import initialize_cycle_table
from .app.services.cycle_orchestrator import run_cycle_tick

def create_app():
    app = Flask(__name__)
    
    # Configure database
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/wucupid')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    CORS(app, resources={r"/api/*": {"origins": ["https://wucupid.com", "http://localhost:3000"]}}, supports_credentials=True)
    
    # Register blueprints
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(cycle_bp, url_prefix='/cycle')
    app.register_blueprint(matches_bp, url_prefix='/matches')
    app.register_blueprint(survey, url_prefix='/survey')
    
    # Initialize cycle table
    with app.app_context():
        initialize_cycle_table()
    
    # Add root routes that run cycle tick
    @app.route('/', methods=['GET'])
    def root():
        """Root health check that also advances cycle if needed"""
        try:
            run_cycle_tick()
        except Exception as e:
            app.logger.debug(f"tick_on_root_error: {e}")
        return "ok", 200
    
    @app.route('/health', methods=['GET'])
    def health():
        """Health check that also advances cycle if needed"""
        try:
            run_cycle_tick()
        except Exception as e:
            app.logger.debug(f"tick_on_health_error: {e}")
        return "ok", 200
    
    # Create tables on startup
    @app.before_request
    def create_tables():
        with app.app_context():
            db.create_all()
    
    return app

# Set the FLASK_ENV explicitly if not already set
if not os.environ.get('FLASK_ENV'):
    os.environ['FLASK_ENV'] = 'production'

app = create_app()

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=False)
