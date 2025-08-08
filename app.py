import os
import logging
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from utils import format_currency, get_default_currency, get_currency_symbol

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
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://localhost/cloudpos")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for API endpoints

# Middleware
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
csrf.init_app(app)

# Login manager configuration
login_manager.login_view = 'auth.login'
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
from blueprints.pos_new import pos_bp
from blueprints.stores import stores_bp
from blueprints.inventory import inventory_bp
from blueprints.customers import customers_bp
from blueprints.reports import reports_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(pos_bp, url_prefix='/pos')
app.register_blueprint(inventory_bp, url_prefix='/inventory')
app.register_blueprint(customers_bp, url_prefix='/customers')
app.register_blueprint(reports_bp, url_prefix='/reports')
app.register_blueprint(stores_bp, url_prefix='/stores')

# Register template filters
app.jinja_env.filters['format_currency'] = format_currency
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

# Create tables and default data
with app.app_context():
    db.create_all()

# Make utility functions available in templates
@app.context_processor
def utility_processor():
    return dict(format_currency=format_currency, get_default_currency=get_default_currency)
    
    # Create default roles and admin user if they don't exist
    from utils import create_default_data
    create_default_data()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
