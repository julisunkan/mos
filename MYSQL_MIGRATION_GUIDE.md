# MySQL Migration Guide for PythonAnywhere

This guide covers migrating your Cloud POS Inventory System from PostgreSQL to MySQL for PythonAnywhere hosting.

## Migration Overview

The system has been updated to support MySQL while maintaining all existing functionality:
- ✅ Database connections updated to use PyMySQL
- ✅ Models optimized for MySQL compatibility 
- ✅ Migration scripts created
- ✅ PythonAnywhere-specific configuration added

## Key Changes Made

### 1. Dependencies Updated
- **Removed**: `psycopg2-binary` (PostgreSQL driver)
- **Added**: `PyMySQL>=1.1.0` (MySQL driver)

### 2. Database Configuration
- Updated `app.py` to use MySQL connection strings
- Added environment variable support for MySQL credentials
- Maintained backward compatibility

### 3. Model Adjustments
- Fixed barcode field to allow NULL values (MySQL compatibility)
- Optimized string lengths for MySQL

## PythonAnywhere Setup Instructions

### Step 1: Create MySQL Database
1. Log into your PythonAnywhere dashboard
2. Go to **Databases** tab
3. Create a new MySQL database: `yourusername$cloudpos`
4. Note your database credentials

### Step 2: Set Environment Variables
In your PythonAnywhere bash console, create a `.env` file:

```bash
cd ~/cloudpos
echo 'MYSQL_HOST="yourusername.mysql.pythonanywhere-services.com"' > .env
echo 'MYSQL_USER="yourusername"' >> .env
echo 'MYSQL_PASSWORD="your_mysql_password"' >> .env
echo 'MYSQL_DATABASE="yourusername$cloudpos"' >> .env
echo 'SESSION_SECRET="your-super-secret-key-change-this"' >> .env
```

### Step 3: Upload Files
Upload all project files to your PythonAnywhere account:
```bash
# In PythonAnywhere bash console
cd ~/
git clone https://your-repo-url.git cloudpos
# OR upload files via Files tab
```

### Step 4: Install Dependencies
```bash
cd ~/cloudpos
pip3.10 install --user Flask Flask-SQLAlchemy Flask-Login Flask-WTF PyMySQL bcrypt Werkzeug email-validator python-dotenv requests Pillow qrcode xlsxwriter reportlab gunicorn Flask-Migrate Flask-CORS WTForms SQLAlchemy
```

### Step 5: Configure WSGI
Edit your WSGI configuration file (`/var/www/yourusername_pythonanywhere_com_wsgi.py`):

```python
import sys
import os

# Add your project directory to the Python path
project_home = '/home/yourusername/cloudpos'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Set environment variables
os.environ['MYSQL_HOST'] = 'yourusername.mysql.pythonanywhere-services.com'
os.environ['MYSQL_USER'] = 'yourusername'
os.environ['MYSQL_PASSWORD'] = 'your_mysql_password'
os.environ['MYSQL_DATABASE'] = 'yourusername$cloudpos'
os.environ['SESSION_SECRET'] = 'your-super-secret-key-change-this'
os.environ['FLASK_ENV'] = 'production'

# Import Flask application
from app import app as application
```

### Step 6: Static Files Configuration
In PythonAnywhere Web tab, add static files mapping:
- **URL**: `/static/`
- **Directory**: `/home/yourusername/cloudpos/static/`

### Step 7: Run Migration
In PythonAnywhere bash console:
```bash
cd ~/cloudpos
python3.10 mysql_setup.py
```

### Step 8: Test Your Application
Visit: `https://yourusername.pythonanywhere.com`

## Default Login Credentials

After migration, use these credentials:
- **Super Admin**: username `superadmin`, password `super123`
- **Admin**: username `admin`, password `admin123`
- **Cashier (Main)**: username `casava`, password `cashier123`
- **Cashier (Fashion)**: username `julisunkan`, password `cashier123`
- **Manager**: username `manager1`, password `manager123`

## Features Preserved

All functionality is maintained after migration:
- ✅ Multi-store inventory management
- ✅ Point of Sale with Amount Tendered and Change fields
- ✅ Customer management
- ✅ Sales reporting and analytics
- ✅ User role management
- ✅ Returns processing
- ✅ Stock level management
- ✅ Form success/error messaging

## Troubleshooting

### Connection Issues
1. Verify MySQL credentials in PythonAnywhere dashboard
2. Check environment variables are set correctly
3. Ensure database name follows PythonAnywhere format: `username$dbname`

### Migration Errors
1. Check MySQL setup script logs
2. Verify all dependencies are installed
3. Ensure WSGI configuration is correct

### Permission Errors
1. Change default passwords after first login
2. Verify user roles are assigned correctly

## Support Files Created

- `mysql_setup.py` - Automated migration script
- `pythonanywhere_config.py` - PythonAnywhere-specific configuration
- `MYSQL_MIGRATION_GUIDE.md` - This guide

## Next Steps

After successful deployment:
1. Change all default passwords
2. Configure your store information
3. Add your products and categories
4. Train users on the system

Your Cloud POS Inventory System is now ready for production on PythonAnywhere with MySQL!