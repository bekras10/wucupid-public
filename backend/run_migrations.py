"""
Run all migration scripts to update the database schema
"""
import os
import importlib.util
import sys

def run_migrations():
    """Run all migration scripts in the migrations directory"""
    print("Running database migrations...")
    
    # Get the migrations directory
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')
    
    # Files to skip (Alembic related files)
    skip_files = ['__init__.py', 'env.py', 'script.py.mako', 'alembic.ini', 'README']
    
    # Find all Python files in the migrations directory that are not in the skip list
    migration_files = [f for f in os.listdir(migrations_dir) 
                      if f.endswith('.py') and f not in skip_files and not os.path.isdir(os.path.join(migrations_dir, f))]
    
    # Sort migration files to ensure they run in order
    migration_files.sort()
    
    # Run each migration
    for migration_file in migration_files:
        print(f"Running migration: {migration_file}")
        
        # Get the full path to the migration file
        file_path = os.path.join(migrations_dir, migration_file)
        
        # Dynamic import of the migration module
        module_name = os.path.splitext(migration_file)[0]
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Run the migration
        if hasattr(module, 'run_migration'):
            module.run_migration()
        else:
            print(f"Warning: Migration {migration_file} has no run_migration() function")
    
    print("All migrations completed successfully")

if __name__ == "__main__":
    run_migrations() 