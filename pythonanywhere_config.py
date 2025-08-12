"""
PythonAnywhere-specific configuration for Cloud POS Inventory System
"""

import os

# PythonAnywhere MySQL Configuration
MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'yourusername.mysql.pythonanywhere-services.com'),
    'user': os.environ.get('MYSQL_USER', 'yourusername'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'yourusername$cloudpos'),
    'charset': 'utf8mb4'
}

# Environment Variables for PythonAnywhere
def set_pythonanywhere_env():
    """Set environment variables for PythonAnywhere deployment"""
    
    # MySQL Database URL
    mysql_url = (
        f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
        f"@{MYSQL_CONFIG['host']}/{MYSQL_CONFIG['database']}"
    )
    os.environ['DATABASE_URL'] = mysql_url
    
    # Flask Configuration
    os.environ['FLASK_ENV'] = 'production'
    os.environ.setdefault('SESSION_SECRET', 'your-secret-key-here-change-in-production')
    
    return True

# WSGI Application for PythonAnywhere
def create_wsgi_app():
    """Create WSGI application for PythonAnywhere"""
    # Set environment variables
    set_pythonanywhere_env()
    
    # Import and return Flask app
    from app import app
    return app

# Instructions for PythonAnywhere Setup
PYTHONANYWHERE_SETUP_INSTRUCTIONS = """
PythonAnywhere Setup Instructions:
================================

1. Database Setup:
   - Go to your PythonAnywhere Dashboard
   - Navigate to Databases tab
   - Create a new MySQL database named: yourusername$cloudpos
   - Note your database credentials

2. Environment Variables:
   Set these in your PythonAnywhere console or .env file:
   
   export MYSQL_HOST="yourusername.mysql.pythonanywhere-services.com"
   export MYSQL_USER="yourusername"
   export MYSQL_PASSWORD="your_mysql_password"
   export MYSQL_DATABASE="yourusername$cloudpos"
   export SESSION_SECRET="your-super-secret-key-here"

3. File Upload:
   - Upload all project files to your PythonAnywhere account
   - Install dependencies: pip install -r requirements.txt (if using requirements.txt)
   - Or use: pip install PyMySQL flask flask-sqlalchemy flask-login etc.

4. WSGI Configuration:
   In your PythonAnywhere WSGI configuration file (/var/www/yourusername_pythonanywhere_com_wsgi.py):
   
   import sys
   import os
   
   # Add your project directory to path
   project_home = '/home/yourusername/cloudpos'
   if project_home not in sys.path:
       sys.path = [project_home] + sys.path
   
   # Import the WSGI application
   from pythonanywhere_config import create_wsgi_app
   application = create_wsgi_app()

5. Database Migration:
   Run the MySQL setup script:
   python3 mysql_setup.py

6. Static Files:
   Configure static files mapping in PythonAnywhere:
   URL: /static/
   Directory: /home/yourusername/cloudpos/static/

7. Test your application:
   Visit: https://yourusername.pythonanywhere.com
"""

if __name__ == "__main__":
    print(PYTHONANYWHERE_SETUP_INSTRUCTIONS)