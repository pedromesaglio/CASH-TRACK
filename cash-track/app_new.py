"""
Cash Track - Personal Finance Manager
Refactored Version with Modular Architecture

This is the development entry point.
For production, use wsgi.py with Gunicorn.
"""

from app.factory import create_app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Run the development server
    app.run(debug=True, port=9000)
