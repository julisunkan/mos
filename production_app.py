import os
import logging
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from utils import format_currency, format_number, get_default_currency, get_currency_symbol

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()

# Create the app
app = Flask(__name__)

# Production configuration
app.secret_key = os.environ.get("SESSION_SECRET")
if not app.secret_key:
    raise RuntimeError("SESSION_SECRET environment variable is required for production")

# Database configuration for production
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is required for production deployment")

# Handle different PostgreSQL URL formats
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_size": 10,
    "pool_recycle": 300,
    "pool_pre_ping": True,
    "pool_timeout": 20,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_ENABLED"] = True

# Production settings
app.config["DEBUG"] = False
app.config["TESTING"] = False

# Security headers middleware
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

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': os.environ.get('FLY_ALLOC_ID', 'dev')})

# Create tables and ensure deployment data exists
with app.app_context():
    try:
        db.create_all()
        
        # Run production data initialization
        def run_production_initialization():
            try:
                app.logger.info("Starting production initialization...")
                from utils import create_default_data
                create_default_data()
                app.logger.info("Production initialization completed successfully")
            except Exception as e:
                app.logger.error(f"Production initialization failed: {e}")
                # Try the migration scripts as fallback
                try:
                    from migrations.simple_deploy_migration import ensure_data_exists
                    app.logger.info("Attempting migration fallback...")
                    ensure_data_exists()
                    app.logger.info("Fallback completed")
                except Exception as fallback_error:
                    app.logger.error(f"Fallback failed: {fallback_error}")
                    app.logger.warning("Starting with empty database - manual setup required")
        
        # Run initialization
        run_production_initialization()
        
    except Exception as e:
        app.logger.error(f"Database initialization failed: {e}")
        raise

# Make utility functions available in templates
@app.context_processor
def utility_processor():
    return dict(format_currency=format_currency, format_number=format_number, get_default_currency=get_default_currency)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)