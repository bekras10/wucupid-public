from app import create_app, db
from app.models.models import User, SurveyResponse, Match, MatchingCycle
from app.models.cycle import initialize_cycle_table
import os

print("Creating application...")
app = create_app()

with app.app_context():
    print("Creating database tables...")
    db.create_all()
    
    print("Initializing cycle...")
    initialize_cycle_table()
    
    print("Database setup complete!") 