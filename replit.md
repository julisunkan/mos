# Overview

Cloud POS & Inventory Manager is a comprehensive Point of Sale and Inventory Management system built with Flask/PostgreSQL. It provides multi-store support, role-based access control, and complete business operations management including POS transactions, inventory tracking, customer management, and reporting. The application is designed for businesses of all sizes with secure authentication and granular permission controls.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Framework
- **Flask Application Factory Pattern**: Modular blueprint-based architecture with separate modules for admin, auth, customers, inventory, POS, and reports
- **SQLAlchemy ORM**: Database abstraction layer with Alembic migrations support for schema management
- **Role-Based Access Control (RBAC)**: Granular permission system with roles (Admin, Manager, Cashier, Accountant) and specific permissions for each feature
- **Flask-Login**: Session-based authentication with bcrypt password hashing and automatic session management

## Database Design
- **Multi-Store Architecture**: Support for multiple store locations with user assignment and inventory tracking per store
- **Hierarchical Categories**: Nested product categories with parent-child relationships
- **Inventory Management**: Real-time stock tracking with minimum stock levels and stock movement history
- **Sales Transaction Model**: Complete transaction recording with line items, tax calculations, and payment methods
- **Customer Management**: Customer profiles with purchase history and grouping capabilities

## Frontend Architecture
- **Bootstrap 5 Dark Theme**: Responsive UI with consistent styling and mobile-first design
- **Jinja2 Templates**: Server-side rendering with template inheritance and component reusability
- **AJAX-Powered POS**: Real-time product search, barcode scanning, and cart management without page reloads
- **Chart.js Integration**: Dashboard analytics with sales trends and performance metrics

## Security Implementation
- **CSRF Protection**: Flask-WTF forms with CSRF tokens for all state-changing operations
- **Admin-Only User Creation**: No public registration - only administrators can create user accounts
- **Permission Decorators**: Function-level access control with permission checking middleware
- **Secure Session Management**: Configurable session secrets with proxy fix for deployment

## API Structure
- **RESTful Endpoints**: JSON APIs for POS operations, product search, and real-time data updates
- **Barcode/SKU Search**: Fast product lookup by multiple identifiers for efficient POS operations
- **Inventory Updates**: Real-time stock level adjustments with transaction logging

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web framework with SQLAlchemy, Login, and WTF extensions
- **PostgreSQL**: Primary database with SQLAlchemy ORM abstraction
- **Werkzeug**: WSGI utilities including security helpers and development server
- **Alembic**: Database migration management (implied by SQLAlchemy setup)

## Frontend Assets
- **Bootstrap 5 CSS**: UI framework with Replit dark theme integration
- **Font Awesome**: Icon library for consistent UI iconography
- **Chart.js**: Client-side charting library for dashboard analytics

## Development Tools
- **Flask Debug Mode**: Development server with auto-reload and debugging capabilities
- **Logging Configuration**: Structured logging for application monitoring and debugging

## Deployment Considerations
- **ProxyFix Middleware**: Configured for reverse proxy deployment scenarios
- **Environment Configuration**: Database URLs and secrets managed through environment variables
- **Session Security**: Configurable secret keys with development defaults