from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    role = db.Column(db.String(20), default='Cashier', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Foreign keys
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'))
    
    # Relationships
    sales = db.relationship('Sale', backref='user', lazy=True)
    default_store = db.relationship('Store', backref='default_users')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def has_permission(self, permission):
        role_permissions = {
            'Admin': ['all'],
            'Manager': ['read_all', 'write_inventory', 'write_customers', 'read_reports'],
            'Cashier': ['read_products', 'write_sales', 'read_customers'],
            'Accountant': ['read_all', 'read_reports', 'write_reports']
        }
        return permission in role_permissions.get(self.role, []) or 'all' in role_permissions.get(self.role, [])
    
    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    products = db.relationship('Product', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    barcode = db.Column(db.String(50), unique=True, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    cost_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    low_stock_threshold = db.Column(db.Integer, nullable=False, default=10)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    tax_rate = db.Column(db.Numeric(5, 2), nullable=False, default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sale_items = db.relationship('SaleItem', backref='product', lazy=True)
    
    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_threshold
    
    @property
    def profit_margin(self):
        if self.cost_price > 0:
            return ((self.selling_price - self.cost_price) / self.cost_price) * 100
        return 0
    
    def __repr__(self):
        return f'<Product {self.name}>'

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    customer_type = db.Column(db.String(20), default='Retail', nullable=False)  # Retail, Wholesale, VIP
    credit_limit = db.Column(db.Numeric(10, 2), default=0.00)
    current_balance = db.Column(db.Numeric(10, 2), default=0.00)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sales = db.relationship('Sale', backref='customer', lazy=True)
    
    def __repr__(self):
        return f'<Customer {self.name}>'

class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    payment_method = db.Column(db.String(20), nullable=False, default='Cash')
    payment_status = db.Column(db.String(20), nullable=False, default='Paid')
    amount_tendered = db.Column(db.Numeric(10, 2), nullable=True)  # For cash payments
    change_amount = db.Column(db.Numeric(10, 2), nullable=True)    # For cash payments
    payment_reference = db.Column(db.String(100), nullable=True)   # For non-cash payments
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    exchange_rate = db.Column(db.Numeric(10, 6), default=1.0)
    loyalty_points_earned = db.Column(db.Integer, default=0)
    loyalty_points_redeemed = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sale_items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')
    store = db.relationship('Store', backref='sales')
    
    def __repr__(self):
        return f'<Sale {self.receipt_number}>'

class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    def __repr__(self):
        return f'<SaleItem Product ID:{self.product_id} x{self.quantity}>'

class Store(db.Model):
    __tablename__ = 'stores'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('UserStore', backref='store', lazy=True)
    stock_items = db.relationship('StoreStock', backref='store', lazy=True)
    
    def __repr__(self):
        return f'<Store {self.name}>'

class UserStore(db.Model):
    __tablename__ = 'user_stores'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='store_assignments')

class StoreStock(db.Model):
    __tablename__ = 'store_stock'
    
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='store_stocks')

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy=True)
    
    def __repr__(self):
        return f'<Supplier {self.name}>'

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    status = db.Column(db.String(20), default='Draft', nullable=False)  # Draft, Sent, Received, Cancelled
    subtotal = db.Column(db.Numeric(10, 2), default=0.00)
    tax_amount = db.Column(db.Numeric(10, 2), default=0.00)
    total_amount = db.Column(db.Numeric(10, 2), default=0.00)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expected_date = db.Column(db.Date)
    received_date = db.Column(db.Date)
    
    # Relationships
    user = db.relationship('User', backref='purchase_orders')
    store = db.relationship('Store', backref='purchase_orders')
    po_items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PurchaseOrder {self.po_number}>'

class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity_ordered = db.Column(db.Integer, nullable=False)
    quantity_received = db.Column(db.Integer, default=0)
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False)
    total_cost = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Relationships
    product = db.relationship('Product', backref='po_items')

class LoyaltyProgram(db.Model):
    __tablename__ = 'loyalty_programs'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    points_balance = db.Column(db.Integer, default=0)
    total_points_earned = db.Column(db.Integer, default=0)
    total_points_redeemed = db.Column(db.Integer, default=0)
    membership_level = db.Column(db.String(20), default='Bronze')  # Bronze, Silver, Gold, Platinum
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('Customer', backref='loyalty_program', uselist=False)
    transactions = db.relationship('LoyaltyTransaction', backref='loyalty_program', lazy=True)

class LoyaltyTransaction(db.Model):
    __tablename__ = 'loyalty_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    loyalty_program_id = db.Column(db.Integer, db.ForeignKey('loyalty_programs.id'), nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'))
    transaction_type = db.Column(db.String(20), nullable=False)  # Earned, Redeemed, Adjusted
    points = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CompanyProfile(db.Model):
    __tablename__ = 'company_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=False)
    logo_url = db.Column(db.String(500))
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    website = db.Column(db.String(200))
    tax_number = db.Column(db.String(50))
    registration_number = db.Column(db.String(50))
    default_currency = db.Column(db.String(3), default='USD')
    default_tax_rate = db.Column(db.Numeric(5, 2), default=0.00)
    receipt_footer = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer)
    old_values = db.Column(db.JSON)
    new_values = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')

class StockTransfer(db.Model):
    __tablename__ = 'stock_transfers'
    
    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    from_store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    to_store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending', nullable=False)  # Pending, In Transit, Completed, Cancelled
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    from_store = db.relationship('Store', foreign_keys=[from_store_id], backref='outbound_transfers')
    to_store = db.relationship('Store', foreign_keys=[to_store_id], backref='inbound_transfers')
    user = db.relationship('User', backref='stock_transfers')
    transfer_items = db.relationship('StockTransferItem', backref='stock_transfer', lazy=True, cascade='all, delete-orphan')

class StockTransferItem(db.Model):
    __tablename__ = 'stock_transfer_items'
    
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('stock_transfers.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    
    # Relationships
    product = db.relationship('Product', backref='transfer_items')

class CashRegister(db.Model):
    __tablename__ = 'cash_registers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('stores.id'), nullable=False)
    opening_balance = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    closing_balance = db.Column(db.Numeric(10, 2))
    total_sales = db.Column(db.Numeric(10, 2), default=0.00)
    cash_in = db.Column(db.Numeric(10, 2), default=0.00)
    cash_out = db.Column(db.Numeric(10, 2), default=0.00)
    is_open = db.Column(db.Boolean, default=True, nullable=False)
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='registers')
    store = db.relationship('Store', backref='registers')
    
    def __repr__(self):
        return f'<CashRegister {self.user.username} - {self.opened_at}>'

# Additional models for enhanced POS features
class ProductImage(db.Model):
    __tablename__ = 'product_images'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    alt_text = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='images')

class HeldSale(db.Model):
    __tablename__ = 'held_sales'
    
    id = db.Column(db.Integer, primary_key=True)
    hold_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    subtotal = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='held_sales')
    customer = db.relationship('Customer', backref='held_sales')

class HeldSaleItem(db.Model):
    __tablename__ = 'held_sale_items'
    
    id = db.Column(db.Integer, primary_key=True)
    held_sale_id = db.Column(db.Integer, db.ForeignKey('held_sales.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Relationships
    held_sale = db.relationship('HeldSale', backref='items')
    product = db.relationship('Product', backref='held_items')

class SaleReturn(db.Model):
    __tablename__ = 'sale_returns'
    
    id = db.Column(db.Integer, primary_key=True)
    return_number = db.Column(db.String(50), unique=True, nullable=False)
    original_sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    return_amount = db.Column(db.Numeric(10, 2), nullable=False)
    return_reason = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default='Pending', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Relationships
    original_sale = db.relationship('Sale', backref='returns')
    processed_by = db.relationship('User', backref='processed_returns')

class SaleReturnItem(db.Model):
    __tablename__ = 'sale_return_items'
    
    id = db.Column(db.Integer, primary_key=True)
    return_id = db.Column(db.Integer, db.ForeignKey('sale_returns.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    original_sale_item_id = db.Column(db.Integer, db.ForeignKey('sale_items.id'), nullable=False)
    quantity_returned = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Relationships
    return_record = db.relationship('SaleReturn', backref='items')
    product = db.relationship('Product', backref='return_items')
    original_item = db.relationship('SaleItem', backref='returns')

class SalePayment(db.Model):
    __tablename__ = 'sale_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    reference_number = db.Column(db.String(100))
    gateway_response = db.Column(db.JSON)
    status = db.Column(db.String(20), default='Completed', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sale = db.relationship('Sale', backref='payments')
