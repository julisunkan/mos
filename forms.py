from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, IntegerField, BooleanField, PasswordField, HiddenField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, ValidationError
from models import User, Product, Category, Customer

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('Password', validators=[DataRequired()])

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(1, 64)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(1, 120)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(1, 64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(1, 64)])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    role = SelectField('Role', choices=[
        ('Admin', 'Admin'),
        ('Manager', 'Manager'),
        ('Cashier', 'Cashier'),
        ('Accountant', 'Accountant')
    ], validators=[DataRequired()])
    is_active = BooleanField('Active')
    
    def __init__(self, user=None, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.user = user
    
    def validate_username(self, field):
        if self.user is None or field.data != self.user.username:
            if User.query.filter_by(username=field.data).first():
                raise ValidationError('Username already exists.')
    
    def validate_email(self, field):
        if self.user is None or field.data != self.user.email:
            if User.query.filter_by(email=field.data).first():
                raise ValidationError('Email already exists.')

class CategoryForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 100)])
    description = TextAreaField('Description')
    is_active = BooleanField('Active', default=True)
    
    def __init__(self, category=None, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.category = category
    
    def validate_name(self, field):
        if self.category is None or field.data != self.category.name:
            if Category.query.filter_by(name=field.data).first():
                raise ValidationError('Category name already exists.')

class ProductForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 200)])
    description = TextAreaField('Description')
    sku = StringField('SKU', validators=[DataRequired(), Length(1, 50)])
    barcode = StringField('Barcode', validators=[Optional(), Length(1, 50)])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    cost_price = DecimalField('Cost Price', validators=[DataRequired(), NumberRange(min=0)])
    selling_price = DecimalField('Selling Price', validators=[DataRequired(), NumberRange(min=0)])
    stock_quantity = IntegerField('Stock Quantity', validators=[DataRequired(), NumberRange(min=0)], default=0)
    low_stock_threshold = IntegerField('Low Stock Threshold', validators=[DataRequired(), NumberRange(min=0)], default=10)
    tax_rate = DecimalField('Tax Rate (%)', validators=[DataRequired(), NumberRange(min=0, max=100)])
    is_active = BooleanField('Active', default=True)
    
    def __init__(self, product=None, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        self.product = product
        self.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(is_active=True).all()]
    
    def validate_sku(self, field):
        if self.product is None or field.data != self.product.sku:
            if Product.query.filter_by(sku=field.data).first():
                raise ValidationError('SKU already exists.')
    
    def validate_barcode(self, field):
        if field.data:
            if self.product is None or field.data != self.product.barcode:
                if Product.query.filter_by(barcode=field.data).first():
                    raise ValidationError('Barcode already exists.')

class CustomerForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(1, 200)])
    email = StringField('Email', validators=[Optional(), Email(), Length(1, 120)])
    phone = StringField('Phone', validators=[Optional(), Length(1, 20)])
    address = TextAreaField('Address')
    customer_type = SelectField('Customer Type', choices=[
        ('Retail', 'Retail'),
        ('Wholesale', 'Wholesale'),
        ('VIP', 'VIP')
    ], validators=[DataRequired()])
    credit_limit = DecimalField('Credit Limit', validators=[DataRequired(), NumberRange(min=0)])
    is_active = BooleanField('Active', default=True)
    
    def __init__(self, customer=None, *args, **kwargs):
        super(CustomerForm, self).__init__(*args, **kwargs)
        self.customer = customer
    
    def validate_email(self, field):
        if field.data:
            if self.customer is None or field.data != self.customer.email:
                if Customer.query.filter_by(email=field.data).first():
                    raise ValidationError('Email already exists.')

class SaleForm(FlaskForm):
    customer_id = SelectField('Customer', coerce=int, validators=[Optional()])
    payment_method = SelectField('Payment Method', choices=[
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Mobile Money', 'Mobile Money')
    ], validators=[DataRequired()])
    discount_amount = DecimalField('Discount', validators=[DataRequired(), NumberRange(min=0)])
    notes = TextAreaField('Notes')
    
    def __init__(self, *args, **kwargs):
        super(SaleForm, self).__init__(*args, **kwargs)
        self.customer_id.choices = [(0, 'Walk-in Customer')] + [(c.id, c.name) for c in Customer.query.filter_by(is_active=True).all()]

class CashRegisterForm(FlaskForm):
    opening_balance = DecimalField('Opening Balance', validators=[DataRequired(), NumberRange(min=0)])
