# Additional models needed for missing features
from app import db
from datetime import datetime

class ProductBatch(db.Model):
    __tablename__ = 'product_batches'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)
    expiry_date = db.Column(db.Date)
    manufacturing_date = db.Column(db.Date)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    cost_price = db.Column(db.Numeric(10, 2), nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='batches')
    supplier = db.relationship('Supplier', backref='batches')

class ProductSerial(db.Model):
    __tablename__ = 'product_serials'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='Available', nullable=False)  # Available, Sold, Returned
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'))
    batch_id = db.Column(db.Integer, db.ForeignKey('product_batches.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product', backref='serials')
    sale = db.relationship('Sale', backref='serials')
    batch = db.relationship('ProductBatch', backref='serials')

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

class SalePayment(db.Model):
    __tablename__ = 'sale_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)  # Cash, Card, Bank Transfer, Mobile Money
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    reference_number = db.Column(db.String(100))
    gateway_response = db.Column(db.JSON)
    status = db.Column(db.String(20), default='Completed', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sale = db.relationship('Sale', backref='payments')

class ExchangeRate(db.Model):
    __tablename__ = 'exchange_rates'
    
    id = db.Column(db.Integer, primary_key=True)
    from_currency = db.Column(db.String(3), nullable=False)
    to_currency = db.Column(db.String(3), nullable=False)
    rate = db.Column(db.Numeric(12, 6), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = db.Column(db.String(50), default='Manual')  # Manual, API
    
    # Unique constraint on currency pair
    __table_args__ = (db.UniqueConstraint('from_currency', 'to_currency'),)

class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    data_type = db.Column(db.String(20), default='string')  # string, integer, boolean, json
    description = db.Column(db.String(200))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)