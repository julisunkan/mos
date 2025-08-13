import os
import logging
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from utils import format_currency, format_number, get_default_currency, get_currency_symbol

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()

# Create the app
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Database configuration with PostgreSQL preference and SQLite fallback
database_url = os.environ.get("DATABASE_URL")

if not database_url:
    # Try PostgreSQL first
    try:
        import psycopg2
        # Try to connect to PostgreSQL with various configurations
        possible_configs = [
            # Unix socket connection
            "postgresql:///postgres?host=/tmp",
            # TCP connection with defaults
            "postgresql://runner@localhost:5432/postgres",
            # Standard localhost connection
            "postgresql://localhost:5432/postgres",
        ]
        
        for config in possible_configs:
            try:
                conn = psycopg2.connect(config)
                conn.close()
                # Create cloudpos database if connection successful
                try:
                    conn = psycopg2.connect(config)
                    conn.autocommit = True
                    cursor = conn.cursor()
                    cursor.execute("CREATE DATABASE cloudpos")
                    cursor.close()
                    conn.close()
                except psycopg2.errors.DuplicateDatabase:
                    pass  # Database already exists
                except Exception:
                    pass  # Database creation failed, might already exist
                
                # Set the working database URL
                database_url = config.replace("/postgres", "/cloudpos")
                print(f"✅ Connected to PostgreSQL: {database_url}")
                break
            except Exception as e:
                continue
    except ImportError:
        pass  # psycopg2 not available

if not database_url:
    # Fall back to SQLite
    database_url = "sqlite:///cloudpos.db"
    print("⚠️  PostgreSQL not available, using SQLite fallback")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for API endpoints

# Production settings
if os.environ.get("FLASK_ENV") == "production":
    app.config["DEBUG"] = False
    app.config["TESTING"] = False
    logging.getLogger().setLevel(logging.INFO)
else:
    app.config["DEBUG"] = True

# Middleware
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)

# Login manager configuration
login_manager.login_view = 'auth.login'  # type: ignore
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return db.session.get(User, int(user_id))

# Import models to ensure they are registered
import models

# Register blueprints
from blueprints.auth import auth_bp
from blueprints.admin import admin_bp
from blueprints.stores import stores_bp
from blueprints.inventory import inventory_bp
from blueprints.customers import customers_bp
from blueprints.reports import reports_bp
from blueprints.sales import sales_bp
from blueprints.returns import returns_bp
from blueprints.store_management import store_management_bp
from blueprints.pos import pos_bp


app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(inventory_bp, url_prefix='/inventory')
app.register_blueprint(customers_bp, url_prefix='/customers')
app.register_blueprint(reports_bp, url_prefix='/reports')
app.register_blueprint(stores_bp, url_prefix='/stores')
app.register_blueprint(sales_bp, url_prefix='/sales')
app.register_blueprint(returns_bp, url_prefix='/returns')
app.register_blueprint(pos_bp, url_prefix='/pos')
app.register_blueprint(store_management_bp, url_prefix='/admin/store_management')

# Register template filters
app.jinja_env.filters['format_currency'] = format_currency
app.jinja_env.filters['format_number'] = format_number
app.jinja_env.globals['get_currency_symbol'] = get_currency_symbol

# Main dashboard route
@app.route('/')
@login_required
def dashboard():
    from models import Product, Sale, Customer
    
    # Dashboard statistics
    total_products = Product.query.count()
    total_customers = Customer.query.count()
    total_sales = Sale.query.count()
    
    # Recent sales
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(5).all()
    
    # Low stock products
    low_stock_products = Product.query.filter(Product.stock_quantity <= Product.low_stock_threshold).limit(5).all()
    
    return render_template('dashboard.html',
                         total_products=total_products,
                         total_customers=total_customers,
                         total_sales=total_sales,
                         recent_sales=recent_sales,
                         low_stock_products=low_stock_products)

@app.route('/api/dashboard/stats')
@login_required
def dashboard_stats_api():
    """API endpoint for dashboard statistics refresh"""
    from models import Product, Sale, Customer
    
    total_products = Product.query.count()
    total_customers = Customer.query.count()
    total_sales = Sale.query.count()
    low_stock_count = Product.query.filter(Product.stock_quantity <= Product.low_stock_threshold).count()
    
    return jsonify({
        'total_products': total_products,
        'total_customers': total_customers,
        'total_sales': total_sales,
        'low_stock_count': low_stock_count
    })

# Create tables and ensure deployment data exists
with app.app_context():
    db.create_all()
    
    # Run deployment migration on startup - moved to after dependencies are loaded
    def run_deployment_migration():
        try:
            from migrations.simple_deploy_migration import ensure_data_exists
            print("🚀 Starting deployment migration...")
            ensure_data_exists()
            print("✅ Deployment migration completed successfully")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            print("🔄 Attempting fallback data seeding...")
            try:
                exec(open('seed_data.py').read())
                print("✅ Fallback seeding completed")
            except Exception as fallback_error:
                print(f"❌ Fallback also failed: {fallback_error}")
                print("⚠️  Starting with empty database - admin setup required")
    
    # Run migration
    run_deployment_migration()
    
    # Create default roles and admin user if they don't exist
    from utils import create_default_data
    create_default_data()

# Make utility functions available in templates
@app.context_processor
def utility_processor():
    return dict(format_currency=format_currency, format_number=format_number, get_default_currency=get_default_currency)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
