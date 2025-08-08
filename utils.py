import os
from datetime import datetime
from app import db
from models import User, Category
from werkzeug.security import generate_password_hash

def create_default_data():
    """Create default roles, categories, and admin user if they don't exist"""
    
    # Create default admin user
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@cloudpos.com',
            first_name='System',
            last_name='Administrator',
            role='Admin',
            is_active=True
        )
        admin.set_password('admin123')  # Change this in production
        db.session.add(admin)
    
    # Create default categories
    default_categories = [
        {'name': 'General', 'description': 'General products'},
        {'name': 'Electronics', 'description': 'Electronic devices and accessories'},
        {'name': 'Clothing', 'description': 'Clothing and apparel'},
        {'name': 'Food & Beverages', 'description': 'Food and drink items'},
        {'name': 'Health & Beauty', 'description': 'Health and beauty products'},
    ]
    
    for cat_data in default_categories:
        category = Category.query.filter_by(name=cat_data['name']).first()
        if not category:
            category = Category(
                name=cat_data['name'],
                description=cat_data['description'],
                is_active=True
            )
            db.session.add(category)
    
    try:
        db.session.commit()
        print("Default data created successfully")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default data: {e}")

def generate_receipt_number():
    """Generate a unique receipt number"""
    from models import Sale
    now = datetime.now()
    date_prefix = now.strftime("%Y%m%d")
    
    # Find the last sale of the day
    last_sale = Sale.query.filter(
        Sale.receipt_number.like(f"{date_prefix}%")
    ).order_by(Sale.receipt_number.desc()).first()
    
    if last_sale:
        # Extract the sequence number and increment
        sequence = int(last_sale.receipt_number[-4:]) + 1
    else:
        sequence = 1
    
    return f"{date_prefix}{sequence:04d}"

def generate_sku():
    """Generate a unique SKU"""
    from models import Product
    import random
    import string
    
    while True:
        # Generate a random SKU (format: SKU-XXXXXX)
        sku = 'SKU-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        # Check if it's unique
        if not Product.query.filter_by(sku=sku).first():
            return sku

def format_currency(amount):
    """Format amount as currency"""
    return f"${amount:,.2f}"

def calculate_tax(amount, tax_rate):
    """Calculate tax amount"""
    return (amount * tax_rate) / 100
