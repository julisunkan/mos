"""
Production deployment migration for Fly.io with PostgreSQL
"""
import os
import sys
from datetime import datetime

def ensure_production_data():
    """Ensure all required data exists for production deployment"""
    
    # Import inside function to avoid circular imports
    from production_app import db
    from models import (User, Store, Category, Product, Customer)
    from werkzeug.security import generate_password_hash
    
    print("🚀 Starting Fly.io production migration...")
    
    try:
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Check if data already exists
        if Company.query.first():
            print("✅ Data already exists - skipping migration")
            return True
        
        # Create company profile
        company = Company(
            name="Cloud POS Solutions",
            address="123 Business Ave, Tech City, TC 12345",
            phone="+1-555-0123",
            email="admin@cloudpos.com",
            website="https://cloudpos.com",
            tax_number="TAX123456789",
            currency_code="USD",
            logo_path=None
        )
        db.session.add(company)
        
        # Create default roles
        roles_data = [
            {"name": "Super Admin", "description": "Full system access"},
            {"name": "Admin", "description": "Administrative access"},
            {"name": "Manager", "description": "Store management access"},
            {"name": "Cashier", "description": "POS and basic operations"}
        ]
        
        roles = {}
        for role_data in roles_data:
            role = Role.query.filter_by(name=role_data["name"]).first()
            if not role:
                role = Role(**role_data)
                db.session.add(role)
                db.session.flush()  # Get the ID
            roles[role_data["name"]] = role
        
        # Create stores
        stores_data = [
            {
                "name": "Main Store",
                "address": "456 Main Street, Downtown, DT 54321",
                "phone": "+1-555-0124",
                "email": "main@cloudpos.com",
                "manager_name": "John Manager",
                "is_active": True
            },
            {
                "name": "Fashion Store",
                "address": "789 Fashion Ave, Style District, SD 98765",
                "phone": "+1-555-0125", 
                "email": "fashion@cloudpos.com",
                "manager_name": "Jane Fashion",
                "is_active": True
            }
        ]
        
        stores = {}
        for store_data in stores_data:
            store = Store(**store_data)
            db.session.add(store)
            db.session.flush()
            stores[store_data["name"]] = store
        
        # Create users with proper roles
        users_data = [
            {
                "username": "superadmin",
                "first_name": "Super",
                "last_name": "Admin", 
                "email": "superadmin@cloudpos.com",
                "password": "super123",
                "role": "Super Admin",
                "is_active": True
            },
            {
                "username": "admin",
                "first_name": "Admin",
                "last_name": "User",
                "email": "admin@cloudpos.com", 
                "password": "admin123",
                "role": "Admin",
                "is_active": True
            },
            {
                "username": "casava",
                "first_name": "Casa",
                "last_name": "Va",
                "email": "casava@cloudpos.com",
                "password": "cashier123",
                "role": "Cashier",
                "is_active": True,
                "store": "Main Store"
            },
            {
                "username": "julisunkan",
                "first_name": "Juli",
                "last_name": "Sunkan",
                "email": "julisunkan@cloudpos.com",
                "password": "cashier123", 
                "role": "Cashier",
                "is_active": True,
                "store": "Fashion Store"
            },
            {
                "username": "manager1",
                "first_name": "Store",
                "last_name": "Manager",
                "email": "manager1@cloudpos.com",
                "password": "manager123",
                "role": "Manager", 
                "is_active": True
            }
        ]
        
        for user_data in users_data:
            user = User(
                username=user_data["username"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                email=user_data["email"],
                password_hash=generate_password_hash(user_data["password"]),
                role=roles[user_data["role"]],
                is_active=user_data["is_active"]
            )
            db.session.add(user)
            db.session.flush()
            
            # Assign user to store if specified
            if "store" in user_data:
                user_store = UserStore(
                    user_id=user.id,
                    store_id=stores[user_data["store"]].id
                )
                db.session.add(user_store)
        
        # Create categories
        categories_data = [
            {"name": "Electronics", "description": "Electronic devices and accessories"},
            {"name": "Food & Beverages", "description": "Food items and drinks"},
            {"name": "Fashion", "description": "Clothing and fashion accessories"},
            {"name": "Home & Garden", "description": "Home and garden products"},
            {"name": "Health & Beauty", "description": "Health and beauty products"}
        ]
        
        categories = {}
        for cat_data in categories_data:
            category = Category(**cat_data)
            db.session.add(category)
            db.session.flush()
            categories[cat_data["name"]] = category
        
        # Create sample products
        products_data = [
            {
                "name": "Wireless Headphones",
                "description": "High-quality wireless headphones",
                "barcode": "WH001234567890",
                "category": "Electronics",
                "price": 79.99,
                "cost": 45.00,
                "stock_quantity": 150,
                "low_stock_threshold": 20
            },
            {
                "name": "Coffee Beans (1kg)",
                "description": "Premium roasted coffee beans",
                "barcode": "CB001234567891", 
                "category": "Food & Beverages",
                "price": 24.99,
                "cost": 12.00,
                "stock_quantity": 200,
                "low_stock_threshold": 30
            },
            {
                "name": "Cotton T-Shirt",
                "description": "100% cotton casual t-shirt",
                "barcode": "CT001234567892",
                "category": "Fashion", 
                "price": 19.99,
                "cost": 8.00,
                "stock_quantity": 100,
                "low_stock_threshold": 25
            }
        ]
        
        for prod_data in products_data:
            product = Product(
                name=prod_data["name"],
                description=prod_data["description"],
                barcode=prod_data["barcode"],
                category=categories[prod_data["category"]],
                price=prod_data["price"],
                cost=prod_data["cost"],
                stock_quantity=prod_data["stock_quantity"],
                low_stock_threshold=prod_data["low_stock_threshold"],
                is_active=True
            )
            db.session.add(product)
            db.session.flush()
            
            # Add products to all stores
            for store in stores.values():
                store_product = StoreProduct(
                    store_id=store.id,
                    product_id=product.id,
                    stock_quantity=prod_data["stock_quantity"],
                    price=prod_data["price"]
                )
                db.session.add(store_product)
        
        # Create sample customers
        customers_data = [
            {
                "first_name": "John",
                "last_name": "Doe", 
                "email": "john.doe@example.com",
                "phone": "+1-555-0001",
                "address": "123 Customer St, City, ST 12345"
            },
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@example.com", 
                "phone": "+1-555-0002",
                "address": "456 Buyer Ave, Town, ST 67890"
            }
        ]
        
        for cust_data in customers_data:
            customer = Customer(**cust_data)
            db.session.add(customer)
        
        # Commit all changes
        db.session.commit()
        
        print("✅ Production migration completed successfully!")
        print("🔒 Security reminder: Change default passwords in production!")
        
        # Print login credentials for production setup
        print("\n📝 Default login credentials:")
        for user_data in users_data:
            print(f"   {user_data['role']} - Username: {user_data['username']}, Password: {user_data['password']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.session.rollback()
        return False

if __name__ == "__main__":
    # Run migration when called directly
    ensure_production_data()