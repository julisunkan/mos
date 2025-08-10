from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, BooleanField, SelectField, SelectMultipleField, PasswordField, DateField
from wtforms.validators import DataRequired, Length, Email, Optional, NumberRange
from wtforms.widgets import CheckboxInput, ListWidget

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=50)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    role = SelectField('Role', choices=[
        ('Admin', 'Admin'),
        ('Manager', 'Manager'), 
        ('Cashier', 'Cashier'),
        ('Accountant', 'Accountant')
    ], validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=255)])
    is_active = BooleanField('Active', default=True)

class CompanyProfileForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired(), Length(max=200)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email()])
    tax_number = StringField('Tax Number', validators=[Optional(), Length(max=50)])
    registration_number = StringField('Registration Number', validators=[Optional(), Length(max=50)])
    website = StringField('Website', validators=[Optional(), Length(max=200)])
    default_currency = SelectField('Default Currency', choices=[
        ('USD', 'US Dollar ($)'),
        ('EUR', 'Euro (€)'),
        ('GBP', 'British Pound (£)'),
        ('NGN', 'Nigerian Naira (₦)'),
        ('KES', 'Kenyan Shilling (KSh)'),
        ('GHS', 'Ghanaian Cedi (₵)')
    ], default='USD')
    default_tax_rate = FloatField('Default Tax Rate (%)', validators=[Optional(), NumberRange(min=0, max=100)], default=0.0)
    receipt_footer = TextAreaField('Receipt Footer', validators=[Optional(), Length(max=500)])
    logo_url = StringField('Logo URL', validators=[Optional(), Length(max=500)])

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class UserStoreAssignmentForm(FlaskForm):
    user_id = SelectField('Select User', coerce=int, validators=[DataRequired()])
    store_ids = MultiCheckboxField('Assign to Stores', coerce=int, validators=[Optional()])

class SaleForm(FlaskForm):
    customer_id = SelectField('Customer', coerce=int, validators=[Optional()])
    payment_method = SelectField('Payment Method', choices=[
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Mobile Money', 'Mobile Money')
    ], default='Cash')
    discount_amount = FloatField('Discount', default=0.0, validators=[Optional(), NumberRange(min=0)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])

class CashRegisterForm(FlaskForm):
    opening_balance = FloatField('Opening Balance', validators=[DataRequired(), NumberRange(min=0)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])

class ReturnForm(FlaskForm):
    sale_id = IntegerField('Sale ID', validators=[DataRequired()])
    return_reason = StringField('Return Reason', validators=[DataRequired(), Length(max=200)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])

class StoreForm(FlaskForm):
    name = StringField('Store Name', validators=[DataRequired(), Length(max=100)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email()])
    manager_id = SelectField('Store Manager', coerce=int, validators=[Optional()])
    is_active = BooleanField('Active', default=True)

class StockTransferForm(FlaskForm):
    from_store_id = SelectField('From Store', coerce=int, validators=[DataRequired()])
    to_store_id = SelectField('To Store', coerce=int, validators=[DataRequired()])
    product_id = SelectField('Product', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])

class PurchaseOrderForm(FlaskForm):
    supplier_id = SelectField('Supplier', coerce=int, validators=[DataRequired()])
    store_id = SelectField('Store', coerce=int, validators=[DataRequired()])
    expected_date = DateField('Expected Delivery Date', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])

class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', validators=[DataRequired(), Length(max=100)])
    contact_person = StringField('Contact Person', validators=[Optional(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    is_active = BooleanField('Active', default=True)

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=200)])
    sku = StringField('SKU', validators=[Optional(), Length(max=50)])
    barcode = StringField('Barcode', validators=[Optional(), Length(max=100)])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    cost_price = FloatField('Cost Price', validators=[DataRequired(), NumberRange(min=0)])
    selling_price = FloatField('Selling Price', validators=[DataRequired(), NumberRange(min=0)])
    stock_quantity = IntegerField('Stock Quantity', validators=[DataRequired(), NumberRange(min=0)])
    low_stock_threshold = IntegerField('Low Stock Threshold', validators=[Optional(), NumberRange(min=0)], default=10)
    tax_rate = FloatField('Tax Rate (%)', validators=[Optional(), NumberRange(min=0, max=100)], default=0)
    store_ids = SelectMultipleField('Available in Stores', coerce=int, validators=[Optional()])
    is_active = BooleanField('Active', default=True)

class CustomerForm(FlaskForm):
    name = StringField('Customer Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    address = TextAreaField('Address', validators=[Optional(), Length(max=500)])
    customer_type = SelectField('Customer Type', choices=[
        ('Retail', 'Retail'),
        ('Wholesale', 'Wholesale'),
        ('VIP', 'VIP')
    ], default='Retail')
    credit_limit = FloatField('Credit Limit', validators=[Optional(), NumberRange(min=0)], default=0.00)
    is_active = BooleanField('Active', default=True)