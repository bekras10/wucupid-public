import sqlite3
from datetime import datetime, timedelta
from .config import TestConfig
import json
import random
import os
from flask import Flask
from . import create_app

def create_test_database():
    """Create a fresh test database with sample users"""
    config = TestConfig()
    
    # Remove existing test database if it exists
    if os.path.exists(config.DATABASE_PATH):
        os.remove(config.DATABASE_PATH)
        print("Removed existing test database")
    
    # Connect to test database
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Create tables if they don't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        gender TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS survey_responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        answers TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user1_id INTEGER NOT NULL,
        user2_id INTEGER NOT NULL,
        score REAL NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user1_id) REFERENCES users (id),
        FOREIGN KEY (user2_id) REFERENCES users (id)
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS matching_cycle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cycle_number INTEGER NOT NULL,
        survey_start_date TEXT NOT NULL,
        survey_end_date TEXT NOT NULL,
        processing_end_date TEXT NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    ''')
    
    # Create test users
    test_users = [
        # Male users
        {"email": "test_male1@example.com", "gender": "Male"},
        {"email": "test_male2@example.com", "gender": "Male"},
        {"email": "test_male3@example.com", "gender": "Male"},
        # Female users
        {"email": "test_female1@example.com", "gender": "Female"},
        {"email": "test_female2@example.com", "gender": "Female"},
        {"email": "test_female3@example.com", "gender": "Female"}
    ]
    
    # Insert test users
    for user in test_users:
        cursor.execute('''
        INSERT INTO users (email, gender, created_at)
        VALUES (?, ?, ?)
        ''', (user["email"], user["gender"], datetime.now().isoformat()))
    
    # Generate random survey responses for each user
    cursor.execute('SELECT id, gender FROM users')
    users = cursor.fetchall()
    
    for user_id, gender in users:
        # Generate random answers (0-4) for each question
        answers = [random.randint(0, 4) for _ in range(39)]  # 39 questions
        cursor.execute('''
        INSERT INTO survey_responses (user_id, answers, created_at)
        VALUES (?, ?, ?)
        ''', (user_id, json.dumps(answers), datetime.now().isoformat()))
    
    # Create a test cycle
    now = datetime.now()
    survey_end = now + timedelta(minutes=1)  # 1 minute survey period
    processing_end = survey_end + timedelta(minutes=1)  # 1 minute processing period
    
    cursor.execute('''
    INSERT INTO matching_cycle 
    (cycle_number, survey_start_date, survey_end_date, processing_end_date, is_active)
    VALUES (?, ?, ?, ?, ?)
    ''', (
        1,
        now.isoformat(),
        survey_end.isoformat(),
        processing_end.isoformat(),
        1
    ))
    
    conn.commit()
    conn.close()
    print("Test database created and populated with sample users")

def run_test_matching():
    """Run the matching algorithm on the test database"""
    # Set test mode environment variable
    os.environ['TEST_MODE'] = 'true'
    
    # Create Flask app with test configuration
    app = create_app()
    
    # Force the cycle to be in processing state
    config = TestConfig()
    conn = sqlite3.connect(config.DATABASE_PATH)
    cursor = conn.cursor()
    
    # Update cycle to be in processing state
    now = datetime.now()
    survey_end = now - timedelta(minutes=1)  # Survey ended 1 minute ago
    processing_end = now + timedelta(minutes=1)  # Processing ends in 1 minute
    
    cursor.execute('''
    UPDATE matching_cycle 
    SET survey_end_date = ?, processing_end_date = ?
    WHERE is_active = 1
    ''', (survey_end.isoformat(), processing_end.isoformat()))
    
    conn.commit()
    conn.close()
    
    # Run the matching algorithm within application context
    with app.app_context():
        from .routes.matches import generate_matches_internal
        result = generate_matches_internal()
        print("Matching algorithm completed")
        print("Result:", result)

if __name__ == "__main__":
    create_test_database()
    run_test_matching() 