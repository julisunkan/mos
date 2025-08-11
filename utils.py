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

def generate_hold_number():
    """Generate a unique hold number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    suffix = ''.join(random.choices(string.digits, k=3))
    return f"HOLD-{timestamp}-{suffix}"

def generate_return_number():
    """Generate a unique return number"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    suffix = ''.join(random.choices(string.digits, k=3))
    return f"RTN-{timestamp}-{suffix}"

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('all'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator to require super admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'Super Admin':
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

def get_default_currency():
    """Get the default currency from company profile"""
    try:
        from models import CompanyProfile
        profile = CompanyProfile.query.first()
        return profile.default_currency if profile else 'USD'
    except Exception:
        # Return default currency if database is not available
        return 'USD'

def get_currency_symbol(currency_code=None):
    """Get currency symbol for a given currency code"""
    if currency_code is None:
        try:
            currency_code = get_default_currency()
        except Exception:
            currency_code = 'USD'
    
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'NGN': '₦',
        'KES': 'KSh',
        'GHS': '₵',
        'JPY': '¥',
        'INR': '₹',
        'CAD': 'C$',
        'AUD': 'A$'
    }
    return currency_symbols.get(currency_code, currency_code + ' ')

def format_currency(amount, currency_code=None):
    """Format amount with appropriate currency symbol and comma separators"""
    if amount is None:
        amount = 0
    
    if currency_code is None:
        currency_code = get_default_currency()
    
    symbol = get_currency_symbol(currency_code)
    
    # Format with 2 decimal places and comma separators
    return f"{symbol}{amount:,.2f}"

def format_number(number):
    """Format number with comma separators"""
    if number is None:
        number = 0
    return f"{number:,}"

def calculate_tax(amount, tax_rate):
    """Calculate tax amount for a given amount and rate"""
    if not amount or not tax_rate:
        return 0
    return amount * (tax_rate / 100)

def log_audit_action(action, entity_type, entity_id=None, old_values=None, new_values=None):
    """Log an audit action"""
    from models import AuditLog
    from app import db
    from flask import request
    
    audit_log = AuditLog()
    audit_log.user_id = current_user.id if current_user.is_authenticated else None
    audit_log.action = action
    audit_log.entity_type = entity_type
    audit_log.entity_id = entity_id
    audit_log.old_values = old_values
    audit_log.new_values = new_values
    audit_log.ip_address = request.remote_addr
    audit_log.user_agent = request.user_agent.string
    
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

# Removed duplicate format_currency function

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
                       UserStore, LoyaltyProgram, Supplier, PaymentMethod, PromotionCode)
    from app import db
    
    try:
        # Create default store
        default_store = Store.query.first()
        if not default_store:
            default_store = Store()
            default_store.name = 'Main Store'
            default_store.address = '123 Main Street, City, Country'
            default_store.phone = '+1-234-567-8900'
            default_store.email = 'store@company.com'
            db.session.add(default_store)
            db.session.commit()
        
        # Create admin user if doesn't exist
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User()
            admin_user.username = 'admin'
            admin_user.email = 'admin@company.com'
            admin_user.first_name = 'System'
            admin_user.last_name = 'Administrator'
            admin_user.role = 'Admin'
            admin_user.store_id = default_store.id
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            
            # Assign admin to default store
            user_store = UserStore()
            user_store.user_id = admin_user.id
            user_store.store_id = default_store.id
            user_store.is_default = True
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
                category = Category()
                category.name = cat_name
                category.description = cat_desc
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
                customer = Customer()
                customer.name = cust_name
                customer.email = cust_email
                customer.phone = cust_phone
                customer.customer_type = cust_type
                customer.credit_limit = 1000.00 if cust_type == 'VIP' else 500.00 if cust_type == 'Wholesale' else 0.00
                db.session.add(customer)
                
                # Create loyalty program for non-walk-in customers
                if cust_name != 'Walk-in Customer':
                    db.session.flush()  # Get customer ID
                    loyalty = LoyaltyProgram()
                    loyalty.customer_id = customer.id
                    loyalty.points_balance = 0
                    loyalty.membership_level = 'Bronze'
                    db.session.add(loyalty)
        
        # Create sample supplier
        if not Supplier.query.first():
            supplier = Supplier()
            supplier.name = 'Tech Supplies Inc.'
            supplier.contact_person = 'Sarah Johnson'
            supplier.email = 'orders@techsupplies.com'
            supplier.phone = '+1-555-0200'
            supplier.address = '456 Industrial Blvd, Tech City, TC 12345'
            db.session.add(supplier)
        
        # Create company profile
        if not CompanyProfile.query.first():
            company = CompanyProfile()
            company.company_name = 'Cloud POS & Inventory Manager'
            company.address = '123 Business Ave, Suite 100, Business City, BC 12345'
            company.phone = '+1-555-CLOUD'
            company.email = 'info@cloudpos.com'
            company.website = 'www.cloudpos.com'
            company.default_currency = 'USD'
            company.default_tax_rate = 8.25
            company.receipt_footer = 'Thank you for your business!'
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
                product = Product()
                product.name = prod_name
                product.description = prod_desc
                product.sku = prod_sku
                product.barcode = prod_barcode
                product.category_id = electronics_cat.id
                product.cost_price = cost
                product.selling_price = price
                product.stock_quantity = stock
                product.low_stock_threshold = threshold
                product.tax_rate = 8.25
                db.session.add(product)
        
        # Create default payment methods
        payment_methods_data = [
            ('Cash', 'cash', True, False, 0.00, 'fas fa-money-bills'),
            ('Credit Card', 'card', True, True, 2.90, 'fas fa-credit-card'),
            ('Debit Card', 'card', True, True, 1.50, 'fas fa-credit-card'),
            ('PayPal', 'digital_wallet', True, True, 3.49, 'fab fa-paypal'),
            ('Apple Pay', 'digital_wallet', True, True, 2.90, 'fab fa-apple-pay'),
            ('Google Pay', 'digital_wallet', True, True, 2.90, 'fab fa-google-pay'),
            ('Bank Transfer', 'bank_transfer', True, True, 0.50, 'fas fa-university')
        ]
        
        for name, type_val, is_active, requires_ref, fee, icon in payment_methods_data:
            if not PaymentMethod.query.filter_by(name=name).first():
                payment_method = PaymentMethod()
                payment_method.name = name
                payment_method.type = type_val
                payment_method.is_active = is_active
                payment_method.requires_reference = requires_ref
                payment_method.processing_fee_percentage = fee
                payment_method.icon = icon
                db.session.add(payment_method)
        
        # Create sample promotion codes
        from datetime import datetime, timedelta
        
        promotion_codes_data = [
            ('WELCOME10', '10% off for new customers', 'percentage', 10.00, 0.00, 25.00, None, 
             datetime.utcnow(), datetime.utcnow() + timedelta(days=365)),
            ('SAVE5', '$5 off any purchase', 'fixed', 5.00, 20.00, None, 100, 
             datetime.utcnow(), datetime.utcnow() + timedelta(days=30)),
            ('BIGDEAL', '15% off orders over $100', 'percentage', 15.00, 100.00, 50.00, 50, 
             datetime.utcnow(), datetime.utcnow() + timedelta(days=60)),
            ('FREESHIP', '$10 off shipping', 'fixed', 10.00, 50.00, None, None, 
             datetime.utcnow(), datetime.utcnow() + timedelta(days=90))
        ]
        
        for code, desc, disc_type, disc_val, min_purchase, max_disc, usage_limit, start_date, end_date in promotion_codes_data:
            if not PromotionCode.query.filter_by(code=code).first():
                promo = PromotionCode()
                promo.code = code
                promo.description = desc
                promo.discount_type = disc_type
                promo.discount_value = disc_val
                promo.min_purchase_amount = min_purchase
                promo.max_discount_amount = max_disc
                promo.usage_limit = usage_limit
                promo.usage_count = 0
                promo.start_date = start_date
                promo.end_date = end_date
                promo.is_active = True
                promo.store_id = None  # Available in all stores
                db.session.add(promo)
        
        db.session.commit()
        print("Default data created successfully")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default data: {str(e)}")
        raise