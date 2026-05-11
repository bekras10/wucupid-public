import os
import sys
from app import create_app

# Set test mode environment variable
os.environ['TEST_MODE'] = 'true'

# Create and run the Flask app
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Use a different port for testing 