# Overview

Cloud POS & Inventory Manager is a comprehensive Point of Sale and Inventory Management system designed for businesses of all sizes. Built with Flask and PostgreSQL, it offers multi-store support, role-based access control, and complete business operations management including POS transactions, inventory tracking, customer management, and reporting. The system aims to provide secure authentication and granular permission controls for efficient business operation. Key capabilities include an advanced POS system with discounts, multiple payment methods, professional receipts, and real-time sales tracking, alongside robust inventory and customer management features.

## Migration Status (August 11, 2025)
Successfully migrated from Replit Agent to standard Replit environment. The application now runs cleanly with:
- PostgreSQL database provisioned and connected
- All dependencies installed via package manager
- Store assignment issues resolved (fixed User-Store relationship mapping)
- Cashier/POS module completely removed and replaced with clean sales system
- New sales system with PDF receipt generation implemented
- Security practices maintained with client/server separation

### Migration Completed (August 11, 2025)
- Fixed store assignment issue: julisunkan cashier properly assigned to Fashion Store (ID: 2)
- Products assigned to Fashion Store: Wireless Mouse (50 units), USB Cable (25 units), Phone Charger (10 units)
- Store-based product filtering working correctly for POS access
- Application running successfully on Replit with all core functionality verified

### Store-Based Product Filtering Implemented (August 11, 2025)
- Cashiers are restricted to products available in their assigned store only
- POS system filters products based on store_stock availability for user's store_id
- Returns system enforces store-based access control
- Demonstration setup: Main Store (tech products) and Fashion Store (clothing) with separate inventories
- Store assignments: julisunkan → Main Store, fashioncashier → Fashion Store

### Complete Refund Approval System Implemented (August 11, 2025)
- Cashiers can submit return requests that go to "Pending" status
- Returns require admin approval before inventory restoration
- Admin interface with approve/reject functionality
- Clear workflow messaging to cashiers about approval requirement
- Inventory only restored when admin approves the return

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Framework
- **Flask Application Factory Pattern**: Modular, blueprint-based architecture for admin, auth, customers, inventory, stores, and reports.
- **SQLAlchemy ORM**: Database abstraction with Alembic for migrations.
- **Role-Based Access Control (RBAC)**: Granular permissions for roles like Admin, Manager, Cashier, Accountant.
- **Flask-Login**: Session-based authentication with bcrypt hashing.

## Database Design
- **Multi-Store Architecture**: Supports multiple store locations with user assignment and per-store inventory tracking.
- **Hierarchical Categories**: Nested product categories.
- **Inventory Management**: Real-time stock tracking, minimum stock levels, and movement history.
- **Sales Transaction Model**: Detailed transaction recording with line items, tax, and payment methods.
- **Customer Management**: Profiles with purchase history.

## Frontend Architecture
- **Mobile App Interface**: Native app styling, status bar, bottom navigation, touch-optimized interactions.
- **Bootstrap 5 Dark Theme**: Responsive, mobile-first UI with app-like visual elements.
- **Jinja2 Templates**: Server-side rendering with template inheritance and mobile-responsive components.
- **AJAX-Powered POS**: Real-time product search, barcode scanning, and cart management without page reloads.
- **Chart.js Integration**: Dashboard analytics for sales trends.
- **Touch-Friendly Design**: Card-based layouts, large touch targets.

## Security Implementation
- **CSRF Protection**: Flask-WTF forms with CSRF tokens.
- **Admin-Only User Creation**: User accounts created solely by administrators.
- **Permission Decorators**: Function-level access control.
- **Secure Session Management**: Configurable session secrets.

## API Structure
- **RESTful Endpoints**: JSON APIs for POS operations, product search, and real-time data updates.
- **Barcode/SKU Search**: Fast product lookup.
- **Inventory Updates**: Real-time stock level adjustments.

## UI/UX Decisions
- Modern, gradient-based design with card layouts and smooth animations.
- Professional, standard-format POS receipt layout with detailed transaction information and dynamic currency.
- Responsive design optimized for desktop and mobile, with improved product grid alignment and consistent product card styling.
- Inline message system replacing popup notifications.

## Feature Specifications
- **Enhanced POS System**: Advanced cart, discounts/promotions, customer management with loyalty points, multiple payment methods (Cash, Card, Digital Wallets, Bank Transfer, Split Payment), sales history, professional receipts (print/email), product catalog with search/barcode lookup, real-time stock monitoring.
- **Comprehensive Refund System**: Full and partial returns, detailed tracking, inventory restoration, admin management with approval/rejection workflow.
- **Multi-Store Product Selection**: Admins can select specific stores for product availability.
- **Store-Filtered POS System**: POS product listings and sales filtered by cashier's assigned store.
- **Cash Register Management**: Opening/closing balances with store association.
- **Supplier Management**: Purchase order system.
- **Stock Management**: Inter-store stock transfers.
- **Customer Loyalty**: Points-based rewards system.
- **Multi-Currency**: Currency support with exchange rates.
- **System Administration**: Company profile settings and audit logging.

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web framework with SQLAlchemy, Login, and WTF extensions.
- **PostgreSQL**: Primary database.
- **Werkzeug**: WSGI utilities.
- **Alembic**: Database migration management.

## Frontend Assets
- **Bootstrap 5 CSS**: UI framework with Replit dark theme.
- **Font Awesome**: Icon library.
- **Chart.js**: Client-side charting library.

## Deployment Considerations
- **ProxyFix Middleware**: Configured for reverse proxy deployment.
- **Environment Configuration**: Database URLs and secrets managed via environment variables.