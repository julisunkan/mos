#!/usr/bin/env python3
"""
Seed script to initialize the database with default data and admin user.
Run this script after setting up the database.
"""

import os
import sys
from werkzeug.security import generate_password_hash

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Store, Category, Product, Customer, CompanyProfile, UserStore

def create_company_profile():
    """Create default company profile"""
    if not CompanyProfile.query.first():
        company = CompanyProfile(
            company_name='Cloud POS Demo Company',
            address='123 Business Street, City, Country',
            phone='+1-555-123-4567',
            email='info@cloudpos.com',
            default_currency='USD',
            default_tax_rate=10.00,
            receipt_footer='Thank you for your business!'
        )
        db.session.add(company)
        db.session.commit()
        print("✓ Company profile created")

def create_default_store():
    """Create a default store"""
    if not Store.query.first():
        store = Store(
            name='Main Store',
            address='123 Main Street, City, Country',
            phone='+1-234-567-8900',
            email='store@company.com',
            is_active=True
        )
        db.session.add(store)
        db.session.commit()
        print("✓ Default store created")
        return store
    else:
        return Store.query.first()

def create_admin_user():
    """Create default admin and super admin users"""
    default_store = create_default_store()
    
    # Create Super Admin user
    if not User.query.filter_by(username='superadmin').first():
        super_admin_user = User(
            username='superadmin',
            email='superadmin@cloudpos.com',
            first_name='Super',
            last_name='Administrator',
            role='Super Admin',
            store_id=default_store.id,
            is_active=True
        )
        super_admin_user.set_password('super123')  # Change this in production!
        db.session.add(super_admin_user)
        db.session.commit()
        
        # Create user-store relationship
        user_store = UserStore(
            user_id=super_admin_user.id,
            store_id=default_store.id,
            is_default=True
        )
        db.session.add(user_store)
        db.session.commit()
        
        print("✓ Super Admin user created (username: superadmin, password: super123)")
    
    # Create regular Admin user
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            email='admin@cloudpos.com',
            first_name='System',
            last_name='Administrator',
            role='Admin',
            store_id=default_store.id,
            is_active=True
        )
        admin_user.set_password('admin123')  # Change this in production!
        db.session.add(admin_user)
        db.session.commit()
        
        # Create user-store relationship
        user_store = UserStore(
            user_id=admin_user.id,
            store_id=default_store.id,
            is_default=True
        )
        db.session.add(user_store)
        db.session.commit()
        
        print("✓ Admin user created (username: admin, password: admin123)")
        print("  ⚠️  IMPORTANT: Change the admin password after first login!")

def create_default_categories():
    """Create default product categories"""
    categories = [
        ('Electronics', 'Electronic devices and accessories'),
        ('Clothing', 'Apparel and fashion items'),
        ('Food & Beverages', 'Food items and drinks'),
        ('Books & Media', 'Books, magazines, and media'),
        ('Home & Garden', 'Home improvement and garden supplies'),
        ('Sports & Outdoors', 'Sports equipment and outdoor gear'),
        ('Health & Beauty', 'Health and beauty products'),
        ('Toys & Games', 'Toys and gaming products'),
    ]
    
    for name, description in categories:
        if not Category.query.filter_by(name=name).first():
            category = Category(
                name=name,
                description=description,
                is_active=True
            )
            db.session.add(category)
    
    db.session.commit()
    print("✓ Default categories created")

def create_sample_products():
    """Create sample products"""
    # Get categories
    electronics = Category.query.filter_by(name='Electronics').first()
    clothing = Category.query.filter_by(name='Clothing').first()
    food = Category.query.filter_by(name='Food & Beverages').first()
    
    if not electronics or not clothing or not food:
        print("⚠️  Categories not found, skipping sample products")
        return
    
    products = [
        {
            'name': 'Wireless Headphones',
            'description': 'Bluetooth wireless headphones with noise cancellation',
            'sku': 'ELE-WH-001',
            'barcode': '1234567890001',
            'category_id': electronics.id,
            'cost_price': 50.00,
            'selling_price': 99.99,
            'stock_quantity': 25,
            'tax_rate': 10.00
        },
        {
            'name': 'Cotton T-Shirt',
            'description': '100% cotton comfortable t-shirt',
            'sku': 'CLO-TS-001',
            'barcode': '1234567890002',
            'category_id': clothing.id,
            'cost_price': 8.00,
            'selling_price': 19.99,
            'stock_quantity': 50,
            'tax_rate': 5.00
        },
        {
            'name': 'Coffee Beans (1kg)',
            'description': 'Premium Arabica coffee beans',
            'sku': 'FOD-CF-001',
            'barcode': '1234567890003',
            'category_id': food.id,
            'cost_price': 12.00,
            'selling_price': 24.99,
            'stock_quantity': 30,
            'tax_rate': 0.00
        }
    ]
    
    for product_data in products:
        if not Product.query.filter_by(sku=product_data['sku']).first():
            product = Product(
                name=product_data['name'],
                description=product_data['description'],
                sku=product_data['sku'],
                barcode=product_data['barcode'],
                category_id=product_data['category_id'],
                cost_price=product_data['cost_price'],
                selling_price=product_data['selling_price'],
                stock_quantity=product_data['stock_quantity'],
                tax_rate=product_data['tax_rate'],
                is_active=True
            )
            db.session.add(product)
    
    db.session.commit()
    print("✓ Sample products created")

def create_sample_customers():
    """Create sample customers"""
    customers = [
        {
            'name': 'John Doe',
            'email': 'john.doe@email.com',
            'phone': '+1-555-0101',
            'address': '123 Customer Street, City, Country',
            'customer_type': 'Retail'
        },
        {
            'name': 'Jane Smith',
            'email': 'jane.smith@email.com',
            'phone': '+1-555-0102',
            'address': '456 Business Ave, City, Country',
            'customer_type': 'Wholesale'
        },
        {
            'name': 'VIP Customer',
            'email': 'vip@email.com',
            'phone': '+1-555-0103',
            'address': '789 Premium Plaza, City, Country',
            'customer_type': 'VIP'
        }
    ]
    
    for customer_data in customers:
        if not Customer.query.filter_by(email=customer_data['email']).first():
            customer = Customer(
                name=customer_data['name'],
                email=customer_data['email'],
                phone=customer_data['phone'],
                address=customer_data['address'],
                customer_type=customer_data['customer_type'],
                is_active=True
            )
            db.session.add(customer)
    
    db.session.commit()
    print("✓ Sample customers created")

def main():
    """Main function to run all seed operations"""
    print("🌱 Starting database seeding...")
    
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            
            # Run seed functions
            create_company_profile()
            create_default_store()
            create_admin_user()
            create_default_categories()
            create_sample_products()
            create_sample_customers()
            
            print("✅ Database seeding completed successfully!")
            print("\n📝 Login credentials:")
            print("   Super Admin - Username: superadmin, Password: super123")
            print("   Admin - Username: admin, Password: admin123")
            print("\n⚠️  Remember to change passwords after first login!")
            
        except Exception as e:
            print(f"❌ Error during seeding: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    main()