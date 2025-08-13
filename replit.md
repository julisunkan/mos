# Cloud POS Inventory System

## Project Overview
A comprehensive Point of Sale (POS) and inventory management system built with Flask, PostgreSQL, and modern web technologies. Successfully migrated from Replit Agent to standard Replit environment.

## Architecture
- **Backend**: Flask with SQLAlchemy ORM
- **Database**: PostgreSQL with proper security configurations
- **Frontend**: Bootstrap with custom CSS styling
- **Authentication**: Flask-Login with role-based access control
- **Security**: CSRF protection, secure session management

## Key Features
- Multi-store inventory management
- Point of Sale interface
- Customer management
- Sales reporting and analytics
- User role management (Admin, Manager, Cashier)
- Returns processing
- Real-time dashboard

## User Preferences
- Background styling: Title text and icons should have transparent backgrounds
- UI theme: Light theme with professional appearance

## Recent Changes
- **2025-08-13**: Successfully migrated project from Replit Agent to Replit
  - Updated database configuration with PostgreSQL preference and SQLite fallback
  - Fixed SESSION_SECRET environment variable configuration
  - Implemented robust database connection handling
  - App now runs consistently with proper error handling
- **2025-08-12**: Successfully migrated project from Replit Agent to Replit
  - Configured PostgreSQL database with proper environment variables
  - Set up Flask application with security best practices
  - Fixed CSS styling to make title text and icon backgrounds transparent
  - Removed purple overlay from all navigation icons
  - Implemented subtle active state indicators (blue tint, enlarged icons, bold text)
  - Added professional footer with brand, version, tagline, and user welcome
  - Created default users and sample data for immediate use
  - All workflows properly configured and running
  - **Route scan completed**: All 43 routes across 10 blueprints verified working
  - **Security check**: All protected routes properly redirect to authentication
  - **Added favicon.ico** to eliminate 404 errors
  - **Form message handling**: Implemented comprehensive success/error message system
    - All forms now display proper success/error messages when submitted
    - Created reusable message component template
    - Updated inventory, customers, admin, and auth blueprints with consistent messaging
    - Both flash messages and direct template messages supported
  - **POS System Enhancements**: Added Amount Tendered and Change fields
    - Fields appear only for cash payments with real-time change calculation
    - Amount validation ensures sufficient payment before processing
    - Backend properly saves tendered amount and change to database
    - Stock levels automatically update after sales (both global and store-specific)
    - Fixed close button (X) styling to be red instead of black
    - Resolved all stock availability issues across all stores (100+ units each)
  - **Database Migration**: Migrated from PostgreSQL to MySQL for PythonAnywhere hosting
    - Updated dependencies: replaced psycopg2-binary with PyMySQL
    - Modified database configuration to support MySQL connection strings
    - Fixed model compatibility issues (barcode field nullable)
    - Created MySQL-specific setup script (mysql_setup.py)
    - Added PythonAnywhere configuration (pythonanywhere_config.py)
    - Created comprehensive migration guide (MYSQL_MIGRATION_GUIDE.md)
    - Maintained all existing functionality during migration

## Default Login Credentials
- Super Admin: username 'superadmin', password 'super123'
- Admin: username 'admin', password 'admin123'
- Cashier (Main): username 'casava', password 'cashier123'
- Cashier (Fashion): username 'julisunkan', password 'cashier123'
- Manager: username 'manager1', password 'manager123'

## Environment Configuration
- DATABASE_URL: Configured for PostgreSQL
- SESSION_SECRET: Secure session key for Flask
- All packages properly installed via uv package manager

## Security Notes
- Change default passwords in production
- CSRF protection enabled
- Secure session management implemented
- Database credentials managed through environment variables