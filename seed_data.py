#!/usr/bin/env python3
"""
Seed script to initialize the database with default roles, permissions, and admin user.
Run this script after setting up the database.
"""

import os
import sys
from werkzeug.security import generate_password_hash

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from models import User, Role, Permission, Store, Category, Product, Customer, Inventory, role_permissions

def create_permissions():
    """Create default permissions"""
    permissions_data = [
        # User Management
        ('user_create', 'Create users'),
        ('user_read', 'View users'),
        ('user_update', 'Update users'),
        ('user_delete', 'Delete users'),
        
        # Role Management
        ('role_create', 'Create roles'),
        ('role_read', 'View roles'),
        ('role_update', 'Update roles'),
        ('role_delete', 'Delete roles'),
        
        # Store Management
        ('store_create', 'Create stores'),
        ('store_read', 'View stores'),
        ('store_update', 'Update stores'),
        ('store_delete', 'Delete stores'),
        
        # Product Management
        ('product_create', 'Create products'),
        ('product_read', 'View products'),
        ('product_update', 'Update products'),
        ('product_delete', 'Delete products'),
        
        # Inventory Management
        ('inventory_read', 'View inventory'),
        ('inventory_update', 'Update inventory'),
        ('inventory_transfer', 'Transfer inventory'),
        
        # POS Operations
        ('pos_access', 'Access POS'),
        ('pos_sales', 'Process sales'),
        ('pos_returns', 'Process returns'),
        ('pos_void', 'Void transactions'),
        
        # Customer Management
        ('customer_create', 'Create customers'),
        ('customer_read', 'View customers'),
        ('customer_update', 'Update customers'),
        ('customer_delete', 'Delete customers'),
        
        # Reports
        ('reports_read', 'View reports'),
        ('reports_export', 'Export reports'),
        
        # Cash Register
        ('register_open', 'Open cash register'),
        ('register_close', 'Close cash register'),
        
        # Settings
        ('settings_read', 'View settings'),
        ('settings_update', 'Update settings'),
    ]
    
    for name, description in permissions_data:
        if not Permission.query.filter_by(name=name).first():
            permission = Permission(name=name, description=description)
            db.session.add(permission)
    
    db.session.commit()
    print("✓ Permissions created")

def create_roles():
    """Create default roles with permissions"""
    # Define roles and their permissions
    roles_data = {
        'Admin': [
            'user_create', 'user_read', 'user_update', 'user_delete',
            'role_create', 'role_read', 'role_update', 'role_delete',
            'store_create', 'store_read', 'store_update', 'store_delete',
            'product_create', 'product_read', 'product_update', 'product_delete',
            'inventory_read', 'inventory_update', 'inventory_transfer',
            'pos_access', 'pos_sales', 'pos_returns', 'pos_void',
            'customer_create', 'customer_read', 'customer_update', 'customer_delete',
            'reports_read', 'reports_export',
            'register_open', 'register_close',
            'settings_read', 'settings_update'
        ],
        'Manager': [
            'user_read',
            'store_read', 'store_update',
            'product_create', 'product_read', 'product_update',
            'inventory_read', 'inventory_update', 'inventory_transfer',
            'pos_access', 'pos_sales', 'pos_returns', 'pos_void',
            'customer_create', 'customer_read', 'customer_update',
            'reports_read', 'reports_export',
            'register_open', 'register_close'
        ],
        'Cashier': [
            'product_read',
            'inventory_read',
            'pos_access', 'pos_sales', 'pos_returns',
            'customer_read', 'customer_update',
            'register_open', 'register_close'
        ],
        'Accountant': [
            'product_read',
            'inventory_read',
            'customer_read',
            'reports_read', 'reports_export',
            'settings_read'
        ]
    }
    
    for role_name, permission_names in roles_data.items():
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name, description=f'{role_name} role with predefined permissions')
            db.session.add(role)
            db.session.flush()  # To get the role.id
        
        # Clear existing permissions
        role.permissions.clear()
        
        # Add permissions
        for perm_name in permission_names:
            permission = Permission.query.filter_by(name=perm_name).first()
            if permission:
                role.permissions.append(permission)
    
    db.session.commit()
    print("✓ Roles created")

def create_default_store():
    """Create a default store"""
    if not Store.query.first():
        store = Store(
            name='Main Store',
            address='123 Business Street, City, Country',
            phone='+1-234-567-8900',
            email='store@cloudpos.com',
            is_active=True
        )
        db.session.add(store)
        db.session.commit()
        print("✓ Default store created")
        return store
    return Store.query.first()

def create_admin_user():
    """Create default admin user"""
    admin_role = Role.query.filter_by(name='Admin').first()
    default_store = Store.query.first()
    
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            email='admin@cloudpos.com',
            first_name='System',
            last_name='Administrator',
            role_id=admin_role.id,
            store_id=default_store.id if default_store else None,
            is_active=True
        )
        admin_user.set_password('admin123')  # Change this in production!
        db.session.add(admin_user)
        db.session.commit()
        print("✓ Admin user created (username: admin, password: admin123)")
        print("  ⚠️  IMPORTANT: Change the admin password after first login!")
    else:
        print("✓ Admin user already exists")

def create_sample_categories():
    """Create sample product categories"""
    categories_data = [
        ('Electronics', 'Electronic devices and accessories'),
        ('Clothing', 'Apparel and fashion items'),
        ('Food & Beverages', 'Food items and drinks'),
        ('Health & Beauty', 'Health and beauty products'),
        ('Home & Garden', 'Home improvement and garden items'),
    ]
    
    for name, description in categories_data:
        if not Category.query.filter_by(name=name).first():
            category = Category(name=name, description=description)
            db.session.add(category)
    
    db.session.commit()
    print("✓ Sample categories created")

def create_sample_products():
    """Create sample products"""
    electronics_cat = Category.query.filter_by(name='Electronics').first()
    clothing_cat = Category.query.filter_by(name='Clothing').first()
    food_cat = Category.query.filter_by(name='Food & Beverages').first()
    
    if not electronics_cat or not clothing_cat or not food_cat:
        print("⚠️  Categories not found, skipping sample products")
        return
    
    products_data = [
        ('Smartphone X1', 'Latest smartphone with advanced features', 'PHONE001', '1234567890123', electronics_cat.id, 500.00, 799.99, 10.0),
        ('Wireless Headphones', 'Bluetooth wireless headphones', 'HEAD001', '1234567890124', electronics_cat.id, 50.00, 99.99, 10.0),
        ('T-Shirt Blue', 'Cotton t-shirt in blue color', 'TSHIRT001', '1234567890125', clothing_cat.id, 10.00, 25.99, 5.0),
        ('Jeans Regular Fit', 'Regular fit jeans', 'JEANS001', '1234567890126', clothing_cat.id, 30.00, 69.99, 5.0),
        ('Coffee Premium', 'Premium coffee beans 500g', 'COFFEE001', '1234567890127', food_cat.id, 8.00, 19.99, 0.0),
        ('Energy Drink', 'Energy drink 250ml', 'ENERGY001', '1234567890128', food_cat.id, 1.50, 3.99, 8.0),
    ]
    
    default_store = Store.query.first()
    
    for name, desc, sku, barcode, cat_id, cost, price, tax in products_data:
        if not Product.query.filter_by(sku=sku).first():
            product = Product(
                name=name,
                description=desc,
                sku=sku,
                barcode=barcode,
                category_id=cat_id,
                cost_price=cost,
                sale_price=price,
                tax_rate=tax,
                is_active=True,
                track_inventory=True
            )
            db.session.add(product)
            db.session.flush()  # To get product.id
            
            # Add inventory for the default store
            if default_store:
                inventory = Inventory(
                    product_id=product.id,
                    store_id=default_store.id,
                    quantity=50,  # Starting with 50 units
                    min_stock=10,
                    max_stock=200
                )
                db.session.add(inventory)
    
    db.session.commit()
    print("✓ Sample products created")

def create_sample_customers():
    """Create sample customers"""
    customers_data = [
        ('John Doe', 'john.doe@email.com', '+1-234-567-8901', '123 Main St, City', 'Retail', 0),
        ('Jane Smith', 'jane.smith@email.com', '+1-234-567-8902', '456 Oak Ave, City', 'VIP', 1000),
        ('Bob Johnson', 'bob.johnson@email.com', '+1-234-567-8903', '789 Pine Rd, City', 'Wholesale', 5000),
        ('Alice Brown', 'alice.brown@email.com', '+1-234-567-8904', '321 Elm St, City', 'Retail', 0),
        ('Charlie Wilson', 'charlie.wilson@email.com', '+1-234-567-8905', '654 Maple Dr, City', 'VIP', 2000),
    ]
    
    for name, email, phone, address, group, credit in customers_data:
        if not Customer.query.filter_by(email=email).first():
            customer = Customer(
                name=name,
                email=email,
                phone=phone,
                address=address,
                customer_group=group,
                credit_limit=credit,
                current_balance=0,
                loyalty_points=0,
                is_active=True
            )
            db.session.add(customer)
    
    db.session.commit()
    print("✓ Sample customers created")

def main():
    """Main function to run all seed operations"""
    print("Starting database seeding...")
    
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Run seed operations
        create_permissions()
        create_roles()
        create_default_store()
        create_admin_user()
        create_sample_categories()
        create_sample_products()
        create_sample_customers()
        
        print("\n🎉 Database seeding completed successfully!")
        print("\nYou can now log in with:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\n⚠️  Remember to change the admin password after first login!")

if __name__ == '__main__':
    main()
