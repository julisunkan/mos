import string
import random
from datetime import datetime
from functools import wraps
from flask import abort
from flask_login import current_user

def generate_sku():
    """Generate a unique SKU"""
    prefix = 'SKU'
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}-{suffix}"

def generate_receipt_number():
    """Generate a unique receipt number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    suffix = ''.join(random.choices(string.digits, k=3))
    return f"RCP-{timestamp}-{suffix}"

def generate_transfer_number():
    """Generate a unique stock transfer number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    suffix = ''.join(random.choices(string.digits, k=3))
    return f"TRF-{timestamp}-{suffix}"

def generate_po_number():
    """Generate a unique purchase order number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    suffix = ''.join(random.choices(string.digits, k=3))
    return f"PO-{timestamp}-{suffix}"

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('all'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def manager_required(f):
    """Decorator to require manager or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not (
            current_user.has_permission('all') or 
            current_user.has_permission('write_inventory')
        ):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def log_audit_action(action, entity_type, entity_id=None, old_values=None, new_values=None):
    """Log an audit action"""
    from models import AuditLog
    from app import db
    from flask import request
    
    audit_log = AuditLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    
    try:
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error logging audit action: {str(e)}")

def calculate_loyalty_points(amount, customer_type='Retail'):
    """Calculate loyalty points based on purchase amount and customer type"""
    rates = {
        'VIP': 2.0,      # 2 points per dollar
        'Wholesale': 1.0,  # 1 point per dollar
        'Retail': 1.0      # 1 point per dollar
    }
    
    rate = rates.get(customer_type, 1.0)
    return int(float(amount) * rate)

def format_currency(amount, currency='USD'):
    """Format currency amount"""
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'NGN': '₦',
        'KES': 'KSh',
        'GHS': '₵'
    }
    
    symbol = symbols.get(currency, currency + ' ')
    return f"{symbol}{amount:,.2f}"

def get_exchange_rate(from_currency, to_currency):
    """Get exchange rate between currencies (placeholder - would integrate with real API)"""
    # In production, this would call a real exchange rate API
    # For now, return 1.0 (no conversion)
    if from_currency == to_currency:
        return 1.0
    
    # Placeholder rates
    rates = {
        'USD': 1.0,
        'EUR': 0.85,
        'GBP': 0.73,
        'NGN': 460.0,
        'KES': 110.0,
        'GHS': 6.0
    }
    
    usd_from = rates.get(from_currency, 1.0)
    usd_to = rates.get(to_currency, 1.0)
    
    return usd_to / usd_from

def send_sms(phone_number, message):
    """Send SMS (placeholder for Twilio integration)"""
    # In production, integrate with Twilio or other SMS service
    print(f"SMS to {phone_number}: {message}")
    return True

def send_email(to_email, subject, message):
    """Send email (placeholder for email service integration)"""
    # In production, integrate with SendGrid, Mailgun, or other email service
    print(f"Email to {to_email}: {subject} - {message}")
    return True

def send_whatsapp(phone_number, message):
    """Send WhatsApp message (placeholder for WhatsApp Business API)"""
    # In production, integrate with WhatsApp Business API
    print(f"WhatsApp to {phone_number}: {message}")
    return True

def calculate_tax(amount, tax_rate):
    """Calculate tax amount"""
    return float(amount) * (float(tax_rate) / 100)

def create_default_data():
    """Create default data for the application"""
    from models import (User, Store, Category, Product, Customer, CompanyProfile, 
                       UserStore, LoyaltyProgram, Supplier)
    from app import db
    
    try:
        # Create default store
        default_store = Store.query.first()
        if not default_store:
            default_store = Store(
                name='Main Store',
                address='123 Main Street, City, Country',
                phone='+1-234-567-8900',
                email='store@company.com'
            )
            db.session.add(default_store)
            db.session.commit()
        
        # Create admin user if doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@company.com',
                first_name='System',
                last_name='Administrator',
                role='Admin',
                store_id=default_store.id
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            
            # Assign admin to default store
            user_store = UserStore(
                user_id=admin_user.id,
                store_id=default_store.id,
                is_default=True
            )
            db.session.add(user_store)
        
        # Create default categories
        categories_data = [
            ('Electronics', 'Electronic devices and accessories'),
            ('Clothing', 'Apparel and fashion items'),
            ('Books', 'Books and educational materials'),
            ('Home & Garden', 'Home improvement and garden supplies'),
            ('Sports & Outdoors', 'Sports equipment and outdoor gear')
        ]
        
        for cat_name, cat_desc in categories_data:
            if not Category.query.filter_by(name=cat_name).first():
                category = Category(name=cat_name, description=cat_desc)
                db.session.add(category)
        
        # Create default customers
        customers_data = [
            ('Walk-in Customer', None, None, 'Retail'),
            ('John Doe', 'john@example.com', '+1-555-0101', 'Retail'),
            ('ABC Corporation', 'orders@abc-corp.com', '+1-555-0102', 'Wholesale'),
            ('VIP Customer', 'vip@example.com', '+1-555-0103', 'VIP')
        ]
        
        for cust_name, cust_email, cust_phone, cust_type in customers_data:
            if not Customer.query.filter_by(name=cust_name).first():
                customer = Customer(
                    name=cust_name,
                    email=cust_email,
                    phone=cust_phone,
                    customer_type=cust_type,
                    credit_limit=1000.00 if cust_type == 'VIP' else 500.00 if cust_type == 'Wholesale' else 0.00
                )
                db.session.add(customer)
                
                # Create loyalty program for non-walk-in customers
                if cust_name != 'Walk-in Customer':
                    db.session.flush()  # Get customer ID
                    loyalty = LoyaltyProgram(
                        customer_id=customer.id,
                        points_balance=0,
                        membership_level='Bronze'
                    )
                    db.session.add(loyalty)
        
        # Create sample supplier
        if not Supplier.query.first():
            supplier = Supplier(
                name='Tech Supplies Inc.',
                contact_person='Sarah Johnson',
                email='orders@techsupplies.com',
                phone='+1-555-0200',
                address='456 Industrial Blvd, Tech City, TC 12345'
            )
            db.session.add(supplier)
        
        # Create company profile
        if not CompanyProfile.query.first():
            company = CompanyProfile(
                company_name='Cloud POS & Inventory Manager',
                address='123 Business Ave, Suite 100, Business City, BC 12345',
                phone='+1-555-CLOUD',
                email='info@cloudpos.com',
                website='www.cloudpos.com',
                default_currency='USD',
                default_tax_rate=8.25,
                receipt_footer='Thank you for your business!'
            )
            db.session.add(company)
        
        # Create sample products
        electronics_cat = Category.query.filter_by(name='Electronics').first()
        if electronics_cat and not Product.query.first():
            products_data = [
                ('Laptop Computer', 'High-performance laptop', generate_sku(), '1234567890123', 800.00, 1200.00, 5, 2),
                ('Wireless Mouse', 'Bluetooth wireless mouse', generate_sku(), '1234567890124', 15.00, 25.00, 50, 10),
                ('USB Cable', 'USB-C to USB-A cable', generate_sku(), '1234567890125', 5.00, 12.00, 100, 20),
                ('Phone Charger', 'Fast charging phone charger', generate_sku(), '1234567890126', 20.00, 35.00, 30, 5),
                ('Bluetooth Headphones', 'Noise-cancelling headphones', generate_sku(), '1234567890127', 100.00, 180.00, 15, 3)
            ]
            
            for prod_name, prod_desc, prod_sku, prod_barcode, cost, price, stock, threshold in products_data:
                product = Product(
                    name=prod_name,
                    description=prod_desc,
                    sku=prod_sku,
                    barcode=prod_barcode,
                    category_id=electronics_cat.id,
                    cost_price=cost,
                    selling_price=price,
                    stock_quantity=stock,
                    low_stock_threshold=threshold,
                    tax_rate=8.25
                )
                db.session.add(product)
        
        db.session.commit()
        print("Default data created successfully")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default data: {str(e)}")
        raise