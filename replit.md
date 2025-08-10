# Overview

Cloud POS & Inventory Manager is a comprehensive Point of Sale and Inventory Management system built with Flask/PostgreSQL. It provides multi-store support, role-based access control, and complete business operations management including POS transactions, inventory tracking, customer management, and reporting. The application is designed for businesses of all sizes with secure authentication and granular permission controls.

## Recent Changes (August 2025)

✅ **Migration Status: COMPLETED** - Successfully migrated from Replit Agent to Replit environment on August 10, 2025. All packages installed, PostgreSQL database configured, admin user created, and application running successfully on port 5000. **Login functionality verified** - User can successfully log in with admin/admin123 credentials and access the full POS dashboard. **Data persistence confirmed** - all user credentials and database data are preserved across application restarts.

✅ **POS Interface Enhancement: COMPLETED** - Fixed product grid alignment and improved user interface on August 10, 2025. Enhanced product layout with proper Bootstrap grid system (col-xl-3, col-lg-4, col-md-4, col-sm-6, col-6) for optimal responsiveness across all device sizes. Improved product cards with consistent height (140px), better spacing, enhanced gradients, and hover effects. Added responsive breakpoints for mobile optimization and proper grid spacing.

✅ **Complete POS System Rebuild: COMPLETED** - Completely recreated POS system from scratch on August 10, 2025 with enhanced multi-store security. Features include:
- **New Clean Architecture**: Built pos_clean.py blueprint with proper separation of concerns
- **Multi-Store Security**: Cashiers can only access and sell products from their assigned store
- **Modern UI**: Responsive design with gradient styling, product search, and shopping cart interface
- **Store-Based Inventory**: Products filtered by StoreStock relationships per store location
- **Secure Transactions**: Sales processing with store validation and inventory updates
- **Cash Register Management**: Opening/closing balances with proper store association
- **Multiple Payment Methods**: Cash, Card, and Digital Wallet support with change calculation
- **Real-time Updates**: Live product search, cart management, and stock level tracking
- **Fixed All Routes**: Updated all template references from pos.index to pos_clean.index

✅ **Multi-Store Product Selection: COMPLETED** - Implemented selective store availability for products. Admins can now choose which specific stores a product should appear in during product creation/editing. Features include:
- SelectMultipleField in ProductForm for store selection with validation
- Updated inventory blueprint to populate store choices and handle selected stores
- Modified product creation to initialize stock only for selected stores (instead of all stores)
- Enhanced product editing with store assignment management (add/remove store associations)
- Improved product form template with checkbox interface for store selection
- Maintains existing StoreStock model relationships for inventory tracking per location

✅ **Store-Filtered POS System: COMPLETED** - Modified POS system to filter products based on cashier's assigned store. Cashiers now only see and can sell products available in their specific store. Features include:
- POS product listing filtered by user's store assignment through UserStore and CashRegister models
- Product search API updated to only return products available in user's current store
- Store-specific stock checking - validates against StoreStock quantities instead of global product stock
- Sales processing updated to deduct from store-specific stock rather than global inventory
- Prevents cashiers from accessing products not assigned to their store location

✅ **User Deletion Fix: COMPLETED** - Fixed database constraint errors when deleting users by properly cleaning up related records. User deletion now safely removes cash registers, sales records, and store assignments before deleting the user to prevent foreign key constraint violations.

✅ **Modern POS Interface: COMPLETED** - Completely rebuilt the POS page from scratch with modern design and enhanced user experience. Features include:
- Beautiful gradient-based design with card layouts and smooth animations
- Responsive design optimized for both desktop and mobile devices
- Real-time product search with debounced input for better performance  
- Interactive shopping cart with quantity controls and item management
- Store-specific product filtering showing only products available in user's assigned store
- Clean payment processing flow with multiple payment method options
- Loading states and comprehensive error handling with user-friendly messages
- Receipt modal with print functionality for completed sales
- Sticky cart sidebar that stays visible while browsing products

✅ **Route Error Fixes: COMPLETED** - Fixed critical route error in admin blueprint UserStoreAssignmentForm where store_ids.choices was not being populated, causing "TypeError: 'NoneType' object is not iterable" errors. Added proper form choice population for both assign_user_stores and edit_user_stores routes. All routes now working correctly.

✅ **Thousand Separator Formatting: COMPLETED** - Implemented comma separators for all monetary values throughout the application (e.g., $1,234.56 instead of $1234.56). Updated format_currency() function, added format_number() filter, and enhanced JavaScript formatting functions. Fixed sales report modal template literals that were displaying raw code instead of formatted currency values.

✅ **Inline Message System: COMPLETED** - Replaced all popup notifications (alert/confirm dialogs) with modern inline message system across the entire application. Messages now appear at the top of pages with auto-hide functionality and better user experience.

✅ **Dynamic Currency Fix: COMPLETED** - Fixed all hardcoded currency symbols in receipt generation (PDF and print templates). All receipts now use dynamic currency from company settings instead of hardcoded "$" symbols. Updated both pos.py and pos_new.py blueprints to use get_currency_symbol() function.

✅ **Comprehensive Refund System: COMPLETED** - Implemented full refund functionality with partial returns support, detailed return tracking, and admin management system. Features include:
- Interactive return modal with item selection and quantity adjustment
- SaleReturn and SaleReturnItem models for proper data tracking  
- Return processing API endpoints with inventory restoration
- Admin returns management page with approval/rejection workflow
- Integration with existing POS system through returns button
- Proper currency formatting and thousand separators in return interfaces
- Return details modal with comprehensive information display

✅ **Enhanced Database Architecture**: Added multi-store support with Store and UserStore models
✅ **Supplier Management**: Purchase order system with supplier relationships  
✅ **Stock Management**: Inter-store stock transfers and inventory tracking per location
✅ **Customer Loyalty**: Points-based rewards system with membership tiers
✅ **Multi-Currency**: Currency support in sales transactions with exchange rates
✅ **System Administration**: Company profile settings and comprehensive audit logging
✅ **Security**: Enhanced role-based permissions with granular access control

**Default Login**: username: `admin`, password: `admin123`

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
- **Mobile App Interface**: Native app styling with status bar, bottom navigation, and touch-optimized interactions
- **Bootstrap 5 Dark Theme**: Responsive UI with mobile-first design and app-like visual elements
- **Jinja2 Templates**: Server-side rendering with template inheritance and mobile-responsive components
- **AJAX-Powered POS**: Real-time product search, barcode scanning, and cart management without page reloads
- **Chart.js Integration**: Dashboard analytics with sales trends and performance metrics
- **Touch-Friendly Design**: Card-based layout, large touch targets, and haptic feedback simulation

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