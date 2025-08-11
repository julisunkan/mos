#!/usr/bin/env python3
"""
Simple Deployment Migration Script
Creates essential data using direct SQL to avoid model conflicts
"""

import os
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db

def execute_sql(sql, params=None):
    """Execute SQL safely with error handling"""
    try:
        if params:
            db.session.execute(db.text(sql), params)
        else:
            db.session.execute(db.text(sql))
        return True
    except Exception as e:
        print(f"SQL Error: {e}")
        return False

def ensure_data_exists():
    """Ensure all critical data exists using direct SQL"""
    print("🚀 Starting simple deployment migration...")
    
    with app.app_context():
        try:
            # Create tables first
            db.create_all()
            print("✓ Database tables ensured")
            
            changes_made = False
            
            # 1. Ensure company profile exists
            result = db.session.execute(db.text("SELECT COUNT(*) FROM company_profiles")).scalar()
            if result == 0:
                execute_sql("""
                    INSERT INTO company_profiles (company_name, address, phone, email, default_currency, default_tax_rate, receipt_footer)
                    VALUES (:name, :address, :phone, :email, :currency, :tax_rate, :footer)
                """, {
                    'name': 'Cloud POS Demo Company',
                    'address': '123 Business Street, City, Country',
                    'phone': '+1-555-123-4567',
                    'email': 'info@cloudpos.com',
                    'currency': 'USD',
                    'tax_rate': 10.00,
                    'footer': 'Thank you for your business!'
                })
                changes_made = True
                print("✓ Company profile created")
            
            # 2. Ensure stores exist
            main_store_exists = db.session.execute(db.text("SELECT COUNT(*) FROM stores WHERE name = 'Main Store'")).scalar() > 0
            fashion_store_exists = db.session.execute(db.text("SELECT COUNT(*) FROM stores WHERE name = 'Fashion Store'")).scalar() > 0
            
            if not main_store_exists:
                execute_sql("""
                    INSERT INTO stores (name, address, phone, email, is_active)
                    VALUES (:name, :address, :phone, :email, :active)
                """, {
                    'name': 'Main Store',
                    'address': '123 Main Street, City, Country',
                    'phone': '+1-234-567-8900',
                    'email': 'mainstore@company.com',
                    'active': True
                })
                changes_made = True
                print("✓ Main Store created")
            
            if not fashion_store_exists:
                execute_sql("""
                    INSERT INTO stores (name, address, phone, email, is_active)
                    VALUES (:name, :address, :phone, :email, :active)
                """, {
                    'name': 'Fashion Store',
                    'address': '456 Fashion Avenue, City, Country',
                    'phone': '+1-234-567-8901',
                    'email': 'fashion@company.com',
                    'active': True
                })
                changes_made = True
                print("✓ Fashion Store created")
            
            # 3. Get store IDs for user creation
            main_store_id = db.session.execute(db.text("SELECT id FROM stores WHERE name = 'Main Store'")).scalar()
            fashion_store_id = db.session.execute(db.text("SELECT id FROM stores WHERE name = 'Fashion Store'")).scalar()
            
            # 4. Ensure admin users exist
            users_to_create = [
                {
                    'username': 'superadmin',
                    'email': 'superadmin@cloudpos.com',
                    'first_name': 'Super',
                    'last_name': 'Administrator',
                    'role': 'Super Admin',
                    'password': 'super123',
                    'store_id': main_store_id
                },
                {
                    'username': 'admin',
                    'email': 'admin@cloudpos.com',
                    'first_name': 'System',
                    'last_name': 'Administrator',
                    'role': 'Admin',
                    'password': 'admin123',
                    'store_id': main_store_id
                },
                {
                    'username': 'casava',
                    'email': 'casava@cloudpos.com',
                    'first_name': 'Casa',
                    'last_name': 'VA',
                    'role': 'Cashier',
                    'password': 'cashier123',
                    'store_id': main_store_id
                },
                {
                    'username': 'julisunkan',
                    'email': 'julisunkan@cloudpos.com',
                    'first_name': 'Juli',
                    'last_name': 'Sunkan',
                    'role': 'Cashier',
                    'password': 'cashier123',
                    'store_id': fashion_store_id
                },
                {
                    'username': 'manager1',
                    'email': 'manager@cloudpos.com',
                    'first_name': 'Store',
                    'last_name': 'Manager',
                    'role': 'Manager',
                    'password': 'manager123',
                    'store_id': main_store_id
                }
            ]
            
            for user_data in users_to_create:
                user_exists = db.session.execute(db.text("SELECT COUNT(*) FROM users WHERE username = :username"), 
                                               {'username': user_data['username']}).scalar() > 0
                
                if not user_exists:
                    password_hash = generate_password_hash(user_data['password'])
                    execute_sql("""
                        INSERT INTO users (username, email, first_name, last_name, password_hash, role, store_id, is_active)
                        VALUES (:username, :email, :first_name, :last_name, :password_hash, :role, :store_id, :is_active)
                    """, {
                        'username': user_data['username'],
                        'email': user_data['email'],
                        'first_name': user_data['first_name'],
                        'last_name': user_data['last_name'],
                        'password_hash': password_hash,
                        'role': user_data['role'],
                        'store_id': user_data['store_id'],
                        'is_active': True
                    })
                    
                    # Get user ID for user-store relationship
                    user_id = db.session.execute(db.text("SELECT id FROM users WHERE username = :username"), 
                                                {'username': user_data['username']}).scalar()
                    
                    # Create user-store relationship
                    execute_sql("""
                        INSERT INTO user_stores (user_id, store_id, is_default)
                        VALUES (:user_id, :store_id, :is_default)
                    """, {
                        'user_id': user_id,
                        'store_id': user_data['store_id'],
                        'is_default': True
                    })
                    
                    changes_made = True
                    print(f"✓ {user_data['role']} user '{user_data['username']}' created")
            
            # 5. Ensure categories exist
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
                cat_exists = db.session.execute(db.text("SELECT COUNT(*) FROM categories WHERE name = :name"), 
                                              {'name': name}).scalar() > 0
                
                if not cat_exists:
                    execute_sql("""
                        INSERT INTO categories (name, description, is_active)
                        VALUES (:name, :description, :is_active)
                    """, {
                        'name': name,
                        'description': description,
                        'is_active': True
                    })
                    changes_made = True
            
            if changes_made:
                print("✓ Categories created")
            
            # 6. Ensure products exist with store assignments
            # Get category IDs
            electronics_id = db.session.execute(db.text("SELECT id FROM categories WHERE name = 'Electronics'")).scalar()
            clothing_id = db.session.execute(db.text("SELECT id FROM categories WHERE name = 'Clothing'")).scalar()
            food_id = db.session.execute(db.text("SELECT id FROM categories WHERE name = 'Food & Beverages'")).scalar()
            
            products_data = [
                # Main Store Products
                {
                    'name': 'Wireless Headphones',
                    'sku': 'ELE-WH-001',
                    'category_id': electronics_id,
                    'cost_price': 50.00,
                    'selling_price': 99.99,
                    'stock_quantity': 25,
                    'store_id': main_store_id
                },
                {
                    'name': 'Coffee Beans (1kg)',
                    'sku': 'FOD-CF-001',
                    'category_id': food_id,
                    'cost_price': 12.00,
                    'selling_price': 24.99,
                    'stock_quantity': 30,
                    'store_id': main_store_id
                },
                # Fashion Store Products
                {
                    'name': 'Cotton T-Shirt',
                    'sku': 'CLO-TS-001',
                    'category_id': clothing_id,
                    'cost_price': 8.00,
                    'selling_price': 19.99,
                    'stock_quantity': 50,
                    'store_id': fashion_store_id
                },
                {
                    'name': 'Designer Jeans',
                    'sku': 'CLO-DJ-001',
                    'category_id': clothing_id,
                    'cost_price': 30.00,
                    'selling_price': 79.99,
                    'stock_quantity': 20,
                    'store_id': fashion_store_id
                },
                {
                    'name': 'Fashion Accessories',
                    'sku': 'CLO-FA-001',
                    'category_id': clothing_id,
                    'cost_price': 5.00,
                    'selling_price': 15.99,
                    'stock_quantity': 15,
                    'store_id': fashion_store_id
                }
            ]
            
            for product_data in products_data:
                prod_exists = db.session.execute(db.text("SELECT COUNT(*) FROM products WHERE sku = :sku"), 
                                               {'sku': product_data['sku']}).scalar() > 0
                
                if not prod_exists and product_data['category_id']:
                    execute_sql("""
                        INSERT INTO products (name, sku, category_id, cost_price, selling_price, stock_quantity, is_active, tax_rate)
                        VALUES (:name, :sku, :category_id, :cost_price, :selling_price, :stock_quantity, :is_active, :tax_rate)
                    """, {
                        'name': product_data['name'],
                        'sku': product_data['sku'],
                        'category_id': product_data['category_id'],
                        'cost_price': product_data['cost_price'],
                        'selling_price': product_data['selling_price'],
                        'stock_quantity': product_data['stock_quantity'],
                        'is_active': True,
                        'tax_rate': 10.00
                    })
                    
                    # Get product ID for store stock
                    product_id = db.session.execute(db.text("SELECT id FROM products WHERE sku = :sku"), 
                                                   {'sku': product_data['sku']}).scalar()
                    
                    # Create store stock entry
                    stock_exists = db.session.execute(db.text("SELECT COUNT(*) FROM store_stock WHERE store_id = :store_id AND product_id = :product_id"), 
                                                    {'store_id': product_data['store_id'], 'product_id': product_id}).scalar() > 0
                    
                    if not stock_exists:
                        execute_sql("""
                            INSERT INTO store_stock (store_id, product_id, quantity, low_stock_threshold)
                            VALUES (:store_id, :product_id, :quantity, :threshold)
                        """, {
                            'store_id': product_data['store_id'],
                            'product_id': product_id,
                            'quantity': product_data['stock_quantity'],
                            'threshold': 5
                        })
                    
                    changes_made = True
                    print(f"✓ Product '{product_data['name']}' created")
            
            # Commit all changes
            db.session.commit()
            
            if changes_made:
                print("✅ Deployment migration completed successfully!")
                print("\n📝 Default login credentials:")
                print("   Super Admin - Username: superadmin, Password: super123")
                print("   Admin - Username: admin, Password: admin123")
                print("   Cashier (Main) - Username: casava, Password: cashier123")
                print("   Cashier (Fashion) - Username: julisunkan, Password: cashier123")
                print("   Manager - Username: manager1, Password: manager123")
            else:
                print("✅ All data already exists - no migration needed")
            
            print("\n🔒 Security reminder: Change default passwords in production!")
            
        except Exception as e:
            print(f"❌ Error during deployment migration: {str(e)}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    ensure_data_exists()