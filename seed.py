#!/usr/bin/env python3
"""
Seed script to create sample data for Cloud POS & Inventory Manager
Run this script to populate the database with test data
"""

from app import app, db
from models import User, Category, Product, Customer, Sale, SaleItem
from utils import generate_receipt_number
from datetime import datetime, timedelta
import random

def create_sample_data():
    """Create sample data for testing"""
    with app.app_context():
        print("Creating sample data...")
        
        # Create sample users
        users_data = [
            {'username': 'manager1', 'email': 'manager@example.com', 'first_name': 'John', 'last_name': 'Manager', 'role': 'Manager'},
            {'username': 'cashier1', 'email': 'cashier1@example.com', 'first_name': 'Jane', 'last_name': 'Cashier', 'role': 'Cashier'},
            {'username': 'cashier2', 'email': 'cashier2@example.com', 'first_name': 'Bob', 'last_name': 'Smith', 'role': 'Cashier'},
        ]
        
        for user_data in users_data:
            if not User.query.filter_by(username=user_data['username']).first():
                user = User(**user_data)
                user.set_password('password123')
                db.session.add(user)
        
        # Create sample products
        electronics = Category.query.filter_by(name='Electronics').first()
        clothing = Category.query.filter_by(name='Clothing').first()
        food = Category.query.filter_by(name='Food & Beverages').first()
        
        if electronics and clothing and food:
            products_data = [
                {'name': 'iPhone 13', 'sku': 'IPH13-001', 'category_id': electronics.id, 'cost_price': 800, 'selling_price': 999, 'stock_quantity': 25, 'tax_rate': 10},
                {'name': 'Samsung Galaxy S21', 'sku': 'SAM21-001', 'category_id': electronics.id, 'cost_price': 700, 'selling_price': 899, 'stock_quantity': 15, 'tax_rate': 10},
                {'name': 'Wireless Headphones', 'sku': 'WH-001', 'category_id': electronics.id, 'cost_price': 50, 'selling_price': 79, 'stock_quantity': 100, 'tax_rate': 10},
                {'name': 'T-Shirt - Blue', 'sku': 'TS-BLU-001', 'category_id': clothing.id, 'cost_price': 8, 'selling_price': 19.99, 'stock_quantity': 50, 'tax_rate': 5},
                {'name': 'Jeans - Black', 'sku': 'JN-BLK-001', 'category_id': clothing.id, 'cost_price': 20, 'selling_price': 49.99, 'stock_quantity': 30, 'tax_rate': 5},
                {'name': 'Coffee - Premium Blend', 'sku': 'CF-PREM-001', 'category_id': food.id, 'cost_price': 5, 'selling_price': 12.99, 'stock_quantity': 200, 'tax_rate': 0},
                {'name': 'Energy Drink', 'sku': 'ED-001', 'category_id': food.id, 'cost_price': 1.5, 'selling_price': 3.99, 'stock_quantity': 150, 'tax_rate': 0},
            ]
            
            for product_data in products_data:
                if not Product.query.filter_by(sku=product_data['sku']).first():
                    product = Product(**product_data)
                    db.session.add(product)
        
        # Create sample customers
        customers_data = [
            {'name': 'Alice Johnson', 'email': 'alice@example.com', 'phone': '555-0101', 'customer_type': 'VIP'},
            {'name': 'Bob Wilson', 'email': 'bob@example.com', 'phone': '555-0102', 'customer_type': 'Retail'},
            {'name': 'Charlie Brown', 'email': 'charlie@example.com', 'phone': '555-0103', 'customer_type': 'Wholesale'},
            {'name': 'Diana Prince', 'email': 'diana@example.com', 'phone': '555-0104', 'customer_type': 'Retail'},
        ]
        
        for customer_data in customers_data:
            if not Customer.query.filter_by(email=customer_data['email']).first():
                customer = Customer(**customer_data)
                db.session.add(customer)
        
        try:
            db.session.commit()
            print("Sample data created successfully!")
            
            # Create some sample sales
            create_sample_sales()
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating sample data: {e}")

def create_sample_sales():
    """Create sample sales transactions"""
    print("Creating sample sales...")
    
    cashier = User.query.filter_by(role='Cashier').first()
    customers = Customer.query.all()
    products = Product.query.all()
    
    if not cashier or not products:
        print("Cannot create sample sales - missing required data")
        return
    
    # Create 10 sample sales over the last week
    for i in range(10):
        sale_date = datetime.now() - timedelta(days=random.randint(0, 7))
        
        sale = Sale()
        sale.receipt_number = generate_receipt_number()
        sale.user_id = cashier.id
        sale.customer_id = random.choice(customers).id if customers and random.random() > 0.5 else None
        sale.payment_method = random.choice(['Cash', 'Card', 'Bank Transfer'])
        sale.created_at = sale_date
        sale.store_id = 1  # Default store
        
        db.session.add(sale)
        db.session.flush()  # Get the sale ID
        
        # Add 1-3 random items to each sale
        num_items = random.randint(1, 3)
        subtotal = 0
        tax_total = 0
        
        for _ in range(num_items):
            product = random.choice(products)
            quantity = random.randint(1, 3)
            unit_price = product.selling_price
            total_price = unit_price * quantity
            
            sale_item = SaleItem()
            sale_item.sale_id = sale.id
            sale_item.product_id = product.id
            sale_item.quantity = quantity
            sale_item.unit_price = unit_price
            sale_item.total_price = total_price
            
            db.session.add(sale_item)
            subtotal += total_price
            tax_total += (total_price * product.tax_rate) / 100
        
        # Update sale totals
        sale.subtotal = subtotal
        sale.tax_amount = tax_total
        sale.total_amount = subtotal + tax_total
    
    try:
        db.session.commit()
        print("Sample sales created successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Error creating sample sales: {e}")

if __name__ == '__main__':
    create_sample_data()
