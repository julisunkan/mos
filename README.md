# Cloud POS & Inventory Manager

A comprehensive Point of Sale and Inventory Management system built with Flask and PostgreSQL.

## Features

- **Multi-Store Support**: Manage multiple store locations
- **Role-Based Access Control**: Admin, Manager, Cashier, and Accountant roles
- **Point of Sale**: Complete POS system with barcode scanning
- **Inventory Management**: Real-time stock tracking and management
- **Customer Management**: Customer profiles with loyalty programs
- **Reporting**: Comprehensive sales and inventory reports
- **Multi-Currency Support**: Support for multiple currencies with exchange rates

## Quick Start

### Default Login Credentials
- **Username**: admin
- **Password**: admin123

⚠️ **Important**: Change the admin password after first login!

## Deployment to Render

This application is configured for easy deployment to Render:

1. **Fork/Clone** this repository
2. **Connect to Render**: 
   - Go to [render.com](https://render.com)
   - Connect your GitHub repository
   - Choose "Web Service" 
3. **Configure**:
   - Build Command: `./build.sh`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 main:app`
   - Environment: Python 3.11.7
4. **Database**: 
   - Add PostgreSQL database service
   - The app will automatically create tables and seed data

### Environment Variables

The following environment variables are automatically configured:
- `DATABASE_URL`: PostgreSQL connection string
- `SESSION_SECRET`: Auto-generated session secret
- `FLASK_ENV`: Set to "production"

## Local Development

1. **Install dependencies**:
   ```bash
   pip install -r pyproject.toml
   ```

2. **Set up database**:
   ```bash
   # Create PostgreSQL database
   createdb cloudpos
   
   # Set environment variable
   export DATABASE_URL="postgresql://localhost/cloudpos"
   ```

3. **Initialize database**:
   ```bash
   python seed_data.py
   ```

4. **Run application**:
   ```bash
   python main.py
   ```

## Project Structure

```
├── app.py              # Flask application factory
├── main.py             # Application entry point
├── models.py           # Database models
├── forms.py            # WTForms definitions
├── utils.py            # Utility functions
├── seed_data.py        # Database seeding script
├── blueprints/         # Application blueprints
│   ├── admin.py        # Admin management
│   ├── auth.py         # Authentication
│   ├── pos.py          # Point of Sale
│   ├── inventory.py    # Inventory management
│   ├── customers.py    # Customer management
│   └── reports.py      # Reporting
├── templates/          # Jinja2 templates
├── static/             # Static assets
└── render.yaml         # Render deployment config
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout

### POS Operations
- `GET /pos/` - POS interface
- `POST /pos/api/sale/process` - Process sale
- `GET /pos/api/products/search` - Search products

### Admin
- `GET /admin/` - Admin dashboard
- `GET /admin/users` - User management
- `GET /admin/settings` - System settings

## Security Features

- CSRF protection on forms
- Password hashing with bcrypt
- Session-based authentication
- Role-based access control
- SQL injection protection via SQLAlchemy ORM

## Production Considerations

- Uses gunicorn WSGI server
- PostgreSQL connection pooling
- Environment-based configuration
- Automatic database migrations
- Error logging and monitoring

## Support

For issues or questions, please check the application logs or contact your system administrator.

## License

This project is proprietary software. All rights reserved.