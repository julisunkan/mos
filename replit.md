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
- **2025-08-12**: Successfully migrated project from Replit Agent to Replit
  - Configured PostgreSQL database with proper environment variables
  - Set up Flask application with security best practices
  - Fixed CSS styling to make title text and icon backgrounds transparent
  - Removed purple overlay from "Home" navigation icon
  - Made active navigation items have transparent backgrounds
  - Created default users and sample data for immediate use
  - All workflows properly configured and running

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