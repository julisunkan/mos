#!/usr/bin/env python3
"""
Deployment Migration Script for Cloud POS & Inventory Manager
Automatically runs on deployment to ensure all critical data exists
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app and db, but get models from the database metadata to avoid conflicts
from app import app, db

def get_model_class(class_name):
    """Safely get model class from registry"""
    try:
        return db.Model.registry._class_registry.get(class_name)
    except:
        return None

# Get model classes dynamically to avoid import conflicts
def get_models():
    """Get all required model classes"""
    models = {}
    model_names = ['User', 'Store', 'Category', 'Product', 'Customer', 
                   'CompanyProfile', 'UserStore', 'Sale', 'SaleItem', 'StoreStock']
    
    with app.app_context():
        # Import models to register them
        import models
        try:
            import models_additional
        except:
            pass
        
        for name in model_names:
            models[name] = get_model_class(name)
    
    return models

def ensure_company_profile(models):
    """Ensure company profile exists"""
    CompanyProfile = models.get('CompanyProfile')
    if not CompanyProfile or not CompanyProfile.query.first():
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
        print("✓ Company profile created")
        return True
    return False

def ensure_default_stores():
    """Ensure default stores exist"""
    stores_created = 0
    
    # Main Store
    if not Store.query.filter_by(name='Main Store').first():
        main_store = Store(
            name='Main Store',
            address='123 Main Street, City, Country',
            phone='+1-234-567-8900',
            email='mainstore@company.com',
            is_active=True
        )
        db.session.add(main_store)
        stores_created += 1
        print("✓ Main Store created")
    
    # Fashion Store
    if not Store.query.filter_by(name='Fashion Store').first():
        fashion_store = Store(
            name='Fashion Store',
            address='456 Fashion Avenue, City, Country',
            phone='+1-234-567-8901',
            email='fashion@company.com',
            is_active=True
        )
        db.session.add(fashion_store)
        stores_created += 1
        print("✓ Fashion Store created")
    
    return stores_created > 0

def ensure_admin_users():
    """Ensure admin users exist"""
    users_created = 0
    main_store = Store.query.filter_by(name='Main Store').first()
    
    if not main_store:
        print("❌ Main Store not found, cannot create admin users")
        return False
    
    # Create Super Admin user
    if not User.query.filter_by(username='superadmin').first():
        super_admin = User(
            username='superadmin',
            email='superadmin@cloudpos.com',
            first_name='Super',
            last_name='Administrator',
            role='Super Admin',
            store_id=main_store.id,
            is_active=True
        )
        super_admin.set_password('super123')
        db.session.add(super_admin)
        db.session.flush()  # Get the ID
        
        # Create user-store relationship
        user_store = UserStore(
            user_id=super_admin.id,
            store_id=main_store.id,
            is_default=True
        )
        db.session.add(user_store)
        users_created += 1
        print("✓ Super Admin user created")
    
    # Create regular Admin user
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@cloudpos.com',
            first_name='System',
            last_name='Administrator',
            role='Admin',
            store_id=main_store.id,
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.flush()  # Get the ID
        
        # Create user-store relationship
        user_store = UserStore(
            user_id=admin.id,
            store_id=main_store.id,
            is_default=True
        )
        db.session.add(user_store)
        users_created += 1
        print("✓ Admin user created")
    
    return users_created > 0

def ensure_operational_users():
    """Ensure operational users (managers, cashiers) exist"""
    users_created = 0
    main_store = Store.query.filter_by(name='Main Store').first()
    fashion_store = Store.query.filter_by(name='Fashion Store').first()
    
    # Create cashiers for both stores
    operational_users = [
        {
            'username': 'casava',
            'email': 'casava@cloudpos.com',
            'first_name': 'Casa',
            'last_name': 'VA',
            'role': 'Cashier',
            'store': main_store,
            'password': 'cashier123'
        },
        {
            'username': 'julisunkan',
            'email': 'julisunkan@cloudpos.com',
            'first_name': 'Juli',
            'last_name': 'Sunkan',
            'role': 'Cashier',
            'store': fashion_store,
            'password': 'cashier123'
        },
        {
            'username': 'manager1',
            'email': 'manager@cloudpos.com',
            'first_name': 'Store',
            'last_name': 'Manager',
            'role': 'Manager',
            'store': main_store,
            'password': 'manager123'
        }
    ]
    
    for user_data in operational_users:
        if not User.query.filter_by(username=user_data['username']).first():
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                role=user_data['role'],
                store_id=user_data['store'].id if user_data['store'] else None,
                is_active=True
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            db.session.flush()
            
            # Create user-store relationship
            if user_data['store']:
                user_store = UserStore(
                    user_id=user.id,
                    store_id=user_data['store'].id,
                    is_default=True
                )
                db.session.add(user_store)
            
            users_created += 1
            print(f"✓ {user_data['role']} user '{user_data['username']}' created")
    
    return users_created > 0

def ensure_categories():
    """Ensure product categories exist"""
    categories_created = 0
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
            categories_created += 1
    
    if categories_created > 0:
        print(f"✓ {categories_created} categories created")
    
    return categories_created > 0

def ensure_products():
    """Ensure products exist with store assignments"""
    products_created = 0
    
    # Get required data
    electronics = Category.query.filter_by(name='Electronics').first()
    clothing = Category.query.filter_by(name='Clothing').first()
    food = Category.query.filter_by(name='Food & Beverages').first()
    main_store = Store.query.filter_by(name='Main Store').first()
    fashion_store = Store.query.filter_by(name='Fashion Store').first()
    
    if not all([electronics, clothing, food, main_store, fashion_store]):
        print("❌ Required categories or stores not found for products")
        return False
    
    products_data = [
        # Main Store Products
        {
            'name': 'Wireless Headphones',
            'description': 'Bluetooth wireless headphones with noise cancellation',
            'sku': 'ELE-WH-001',
            'barcode': '1234567890001',
            'category_id': electronics.id,
            'cost_price': 50.00,
            'selling_price': 99.99,
            'stock_quantity': 25,
            'tax_rate': 10.00,
            'stores': [main_store]
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
            'tax_rate': 0.00,
            'stores': [main_store]
        },
        # Fashion Store Products
        {
            'name': 'Cotton T-Shirt',
            'description': '100% cotton comfortable t-shirt',
            'sku': 'CLO-TS-001',
            'barcode': '1234567890002',
            'category_id': clothing.id,
            'cost_price': 8.00,
            'selling_price': 19.99,
            'stock_quantity': 50,
            'tax_rate': 5.00,
            'stores': [fashion_store]
        },
        {
            'name': 'Designer Jeans',
            'description': 'Premium designer jeans',
            'sku': 'CLO-DJ-001',
            'barcode': '1234567890004',
            'category_id': clothing.id,
            'cost_price': 30.00,
            'selling_price': 79.99,
            'stock_quantity': 20,
            'tax_rate': 5.00,
            'stores': [fashion_store]
        },
        {
            'name': 'Fashion Accessories',
            'description': 'Trendy fashion accessories',
            'sku': 'CLO-FA-001',
            'barcode': '1234567890005',
            'category_id': clothing.id,
            'cost_price': 5.00,
            'selling_price': 15.99,
            'stock_quantity': 15,
            'tax_rate': 5.00,
            'stores': [fashion_store]
        }
    ]
    
    for product_data in products_data:
        if not Product.query.filter_by(sku=product_data['sku']).first():
            # Create product
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
            db.session.flush()  # Get the ID
            
            # Create store stock entries
            for store in product_data['stores']:
                store_stock = StoreStock(
                    store_id=store.id,
                    product_id=product.id,
                    quantity=product_data['stock_quantity'],
                    low_stock_threshold=5
                )
                db.session.add(store_stock)
            
            products_created += 1
            print(f"✓ Product '{product_data['name']}' created")
    
    return products_created > 0

def ensure_customers():
    """Ensure sample customers exist"""
    customers_created = 0
    customers_data = [
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
    
    for customer_data in customers_data:
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
            customers_created += 1
    
    if customers_created > 0:
        print(f"✓ {customers_created} customers created")
    
    return customers_created > 0

def run_deployment_migration():
    """Main function to run all deployment migrations"""
    print("🚀 Starting deployment migration...")
    print(f"📅 Migration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    with app.app_context():
        try:
            # Create all tables first
            db.create_all()
            print("✓ Database tables ensured")
            
            # Get model classes
            models = get_models()
            changes_made = False
            
            # Run migration functions with models
            if ensure_company_profile(models):
                changes_made = True
            
            if ensure_default_stores(models):
                changes_made = True
                db.session.commit()  # Commit stores before users
            
            if ensure_admin_users(models):
                changes_made = True
            
            if ensure_operational_users(models):
                changes_made = True
            
            if ensure_categories(models):
                changes_made = True
                db.session.commit()  # Commit categories before products
            
            if ensure_products(models):
                changes_made = True
            
            if ensure_customers(models):
                changes_made = True
            
            # Final commit
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
    run_deployment_migration()