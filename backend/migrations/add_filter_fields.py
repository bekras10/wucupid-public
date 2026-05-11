"""
Migration script to add filter fields to User model
"""
from app import create_app, db
from sqlalchemy import Column, String, JSON, inspect
from sqlalchemy.sql import text

app = create_app()

def run_migration():
    """Add filter fields to the users table"""
    with app.app_context():
        # Get a PostgreSQL inspector
        inspector = inspect(db.engine)
        
        # Get existing columns
        existing_columns = [column['name'] for column in inspector.get_columns('users')]
        print(f"Existing columns: {existing_columns}")
        
        # Define the new columns to add
        columns_to_add = {
            'name': 'VARCHAR(255)',
            'academic_year': 'VARCHAR(20)',
            'preferred_years': 'JSON',
            'religion': 'VARCHAR(50)',
            'preferred_religions': 'JSON',
            'political_view': 'VARCHAR(50)',
            'preferred_political_views': 'JSON',
            'sexual_orientation': 'VARCHAR(20)'
        }
        
        # Start a transaction
        with db.engine.begin() as conn:
            # Add columns that don't already exist
            for column_name, column_type in columns_to_add.items():
                if column_name not in existing_columns:
                    try:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))
                        print(f"Added column '{column_name}' to users table")
                    except Exception as e:
                        print(f"Error adding column '{column_name}': {str(e)}")
                else:
                    print(f"Column '{column_name}' already exists in users table")
            
        print("Migration completed successfully")

if __name__ == "__main__":
    run_migration() 