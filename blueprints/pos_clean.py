from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import Product, Customer, Sale, SaleItem, CashRegister, UserStore, StoreStock, Store
from app import db
from utils import generate_receipt_number, format_currency, get_currency_symbol
from datetime import datetime
from decimal import Decimal
import logging

pos_bp = Blueprint('pos_clean', __name__)

def get_user_store():
    """Get the user's assigned store"""
    user_store = UserStore.query.filter_by(user_id=current_user.id).first()
    if not user_store:
        return None
    return user_store.store

def get_user_cash_register():
    """Get the user's open cash register"""
    user_store = get_user_store()
    if not user_store:
        return None
    
    return CashRegister.query.filter_by(
        user_id=current_user.id,
        store_id=user_store.id,
        is_open=True
    ).first()

def get_store_products(store_id, search_term=None):
    """Get products available in the specific store"""
    # Base query for products that have stock in this store
    query = db.session.query(Product).join(StoreStock).filter(
        StoreStock.store_id == store_id,
        StoreStock.quantity > 0,
        Product.is_active == True
    )
    
    # Add search filter if provided
    if search_term and len(search_term.strip()) >= 2:
        search_filter = db.or_(
            Product.name.ilike(f'%{search_term}%'),
            Product.sku.ilike(f'%{search_term}%'),
            Product.barcode.ilike(f'%{search_term}%')
        )
        query = query.filter(search_filter)
    
    return query.order_by(Product.name).all()

@pos_bp.route('/')
@login_required
def index():
    """Main POS interface"""
    # Check if user has a store assignment
    user_store = get_user_store()
    if not user_store:
        flash('You are not assigned to any store. Please contact your administrator.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if user has an open cash register
    cash_register = get_user_cash_register()
    if not cash_register:
        return redirect(url_for('pos_clean.open_register'))
    
    # Get products available in this store
    products = get_store_products(user_store.id)
    
    # Get customers
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    
    return render_template('pos/pos_clean.html', 
                         products=products,
                         customers=customers,
                         store=user_store,
                         cash_register=cash_register)

@pos_bp.route('/enhanced')
@login_required
def enhanced():
    """Enhanced POS interface with advanced features"""
    # Check if user has a store assignment
    user_store = get_user_store()
    if not user_store:
        flash('You are not assigned to any store. Please contact your administrator.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if user has an open cash register
    cash_register = get_user_cash_register()
    if not cash_register:
        return redirect(url_for('pos_clean.open_register'))
    
    # Get products available in this store
    products = get_store_products(user_store.id)
    
    # Get customers
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    
    # Get today's date for sales history default
    from datetime import date
    today = date.today().isoformat()
    
    return render_template('pos/pos_enhanced.html', 
                         products=products,
                         customers=customers,
                         store=user_store,
                         cash_register=cash_register,
                         today=today)

@pos_bp.route('/register/open', methods=['GET', 'POST'])
@login_required
def open_register():
    """Open cash register"""
    user_store = get_user_store()
    if not user_store:
        flash('You are not assigned to any store.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if user already has an open register
    existing_register = get_user_cash_register()
    if existing_register:
        return redirect(url_for('pos_clean.index'))
    
    if request.method == 'POST':
        try:
            opening_balance = Decimal(request.form.get('opening_balance', '0.00'))
            
            # Create new cash register
            cash_register = CashRegister()
            cash_register.user_id = current_user.id
            cash_register.store_id = user_store.id
            cash_register.opening_balance = opening_balance
            cash_register.closing_balance = 0
            cash_register.total_sales = 0
            cash_register.cash_in = 0
            cash_register.cash_out = 0
            cash_register.is_open = True
            cash_register.opened_at = datetime.utcnow()
            
            db.session.add(cash_register)
            db.session.commit()
            
            flash(f'Cash register opened with {format_currency(opening_balance)}', 'success')
            return redirect(url_for('pos_clean.index'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error opening register: {e}')
            flash('Error opening register. Please try again.', 'error')
    
    return render_template('pos/register.html', store=user_store)

@pos_bp.route('/register/close', methods=['POST'])
@login_required
def close_register():
    """Close cash register"""
    cash_register = get_user_cash_register()
    if not cash_register:
        return jsonify({'success': False, 'error': 'No open cash register found.'})
    
    try:
        # Calculate total sales for cash payments since register opened
        total_cash_sales = db.session.query(db.func.sum(Sale.total_amount)).filter(
            Sale.user_id == current_user.id,
            Sale.store_id == cash_register.store_id,
            Sale.payment_method == 'Cash',
            Sale.created_at >= cash_register.opened_at
        ).scalar() or Decimal('0.00')
        
        # Update register
        cash_register.total_sales = total_cash_sales
        cash_register.closing_balance = cash_register.opening_balance + total_cash_sales
        cash_register.is_open = False
        cash_register.closed_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Register closed. Closing balance: {format_currency(cash_register.closing_balance)}',
            'closing_balance': float(cash_register.closing_balance)
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f'Error closing register: {e}')
        return jsonify({'success': False, 'error': 'Error closing register. Please try again.'})

@pos_bp.route('/api/products/search')
@login_required
def search_products():
    """Search products in user's store"""
    user_store = get_user_store()
    if not user_store:
        return jsonify({'error': 'No store assigned'}), 400
    
    search_term = request.args.get('q', '').strip()
    if len(search_term) < 2:
        return jsonify([])
    
    try:
        products = get_store_products(user_store.id, search_term)
        
        results = []
        for product in products:
            store_stock = product.get_store_stock(user_store.id)
            results.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': float(product.selling_price),
                'stock': store_stock,
                'tax_rate': float(product.tax_rate or 0)
            })
        
        return jsonify(results)
        
    except Exception as e:
        logging.error(f'Error searching products: {e}')
        return jsonify({'error': 'Search failed'}), 500

@pos_bp.route('/api/sale/process', methods=['POST'])
@login_required
def process_sale():
    """Process a sale transaction"""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'items' not in data or not data['items']:
            return jsonify({'success': False, 'error': 'No items in cart'}), 400
        
        # Get user store and cash register
        user_store = get_user_store()
        cash_register = get_user_cash_register()
        
        if not user_store:
            return jsonify({'success': False, 'error': 'No store assigned'}), 400
        
        if not cash_register:
            return jsonify({'success': False, 'error': 'No open cash register'}), 400
        
        # Validate all items and check stock
        sale_items = []
        subtotal = Decimal('0.00')
        total_tax = Decimal('0.00')
        
        for item_data in data['items']:
            product = Product.query.get(item_data['product_id'])
            if not product or not product.is_active:
                return jsonify({'success': False, 'error': f'Product not found'}), 400
            
            # Check store stock
            store_stock = product.get_store_stock(user_store.id)
            requested_qty = int(item_data['quantity'])
            
            if store_stock < requested_qty:
                return jsonify({
                    'success': False, 
                    'error': f'Insufficient stock for {product.name}. Available: {store_stock}'
                }), 400
            
            # Calculate amounts
            unit_price = Decimal(str(item_data['unit_price']))
            line_total = unit_price * requested_qty
            tax_amount = line_total * (product.tax_rate / 100) if product.tax_rate else Decimal('0.00')
            
            subtotal += line_total
            total_tax += tax_amount
            
            sale_items.append({
                'product': product,
                'quantity': requested_qty,
                'unit_price': unit_price,
                'line_total': line_total,
                'tax_amount': tax_amount
            })
        
        # Calculate totals
        discount = Decimal(str(data.get('discount', '0.00')))
        total_amount = subtotal + total_tax - discount
        
        # Create sale record
        sale = Sale()
        sale.receipt_number = generate_receipt_number()
        sale.user_id = current_user.id
        sale.customer_id = data.get('customer_id') if data.get('customer_id') else None
        sale.store_id = user_store.id
        sale.subtotal = subtotal
        sale.tax_amount = total_tax
        sale.discount_amount = discount
        sale.total_amount = total_amount
        sale.payment_method = data.get('payment_method', 'Cash')
        sale.payment_status = 'Paid'
        sale.currency = get_currency_symbol()
        sale.notes = data.get('notes', '')
        
        # Handle cash payment details
        if sale.payment_method == 'Cash':
            amount_tendered = Decimal(str(data.get('amount_tendered', total_amount)))
            sale.amount_tendered = amount_tendered
            sale.change_amount = amount_tendered - total_amount
        else:
            sale.amount_tendered = total_amount
            sale.change_amount = Decimal('0.00')
        
        db.session.add(sale)
        db.session.flush()  # Get sale ID
        
        # Create sale items and update stock
        for item_data in sale_items:
            sale_item = SaleItem()
            sale_item.sale_id = sale.id
            sale_item.product_id = item_data['product'].id
            sale_item.quantity = item_data['quantity']
            sale_item.unit_price = item_data['unit_price']
            sale_item.total_price = item_data['line_total']
            
            db.session.add(sale_item)
            
            # Update store stock
            current_stock = item_data['product'].get_store_stock(user_store.id)
            new_stock = current_stock - item_data['quantity']
            item_data['product'].set_store_stock(user_store.id, new_stock)
        
        # Update cash register if cash payment
        if sale.payment_method == 'Cash':
            cash_register.total_sales = (cash_register.total_sales or Decimal('0.00')) + total_amount
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'receipt_number': sale.receipt_number,
            'total_amount': float(total_amount),
            'change_amount': float(sale.change_amount or 0),
            'message': 'Sale completed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f'Error processing sale: {e}')
        return jsonify({'success': False, 'error': 'Sale processing failed'}), 500

@pos_bp.route('/api/promo-code/validate', methods=['POST'])
@login_required
def validate_promo_code():
    """Validate a promo code"""
    try:
        data = request.get_json()
        code = data.get('code', '').strip().upper()
        subtotal = Decimal(str(data.get('subtotal', 0)))
        
        if not code:
            return jsonify({'error': 'Promo code is required'}), 400
        
        user_store = get_user_store()
        if not user_store:
            return jsonify({'error': 'No store assigned'}), 400
        
        # Import PromotionCode here to avoid circular imports
        from models import PromotionCode
        
        # Find promo code
        promo = PromotionCode.query.filter_by(code=code, is_active=True).first()
        
        if not promo:
            return jsonify({'error': 'Invalid promo code'}), 400
        
        if not promo.is_valid():
            return jsonify({'error': 'Promo code has expired or reached usage limit'}), 400
        
        if promo.store_id and promo.store_id != user_store.id:
            return jsonify({'error': 'Promo code not valid for this store'}), 400
        
        if subtotal < promo.min_purchase_amount:
            return jsonify({'error': f'Minimum purchase amount is ${promo.min_purchase_amount}'}), 400
        
        # Calculate discount
        if promo.discount_type == 'percentage':
            discount_amount = (subtotal * promo.discount_value) / 100
            if promo.max_discount_amount:
                discount_amount = min(discount_amount, promo.max_discount_amount)
        else:  # fixed
            discount_amount = min(promo.discount_value, subtotal)
        
        return jsonify({
            'valid': True,
            'discount_type': promo.discount_type,
            'discount_value': float(promo.discount_value),
            'discount_amount': float(discount_amount),
            'description': promo.description
        })
        
    except Exception as e:
        logging.error(f'Error validating promo code: {e}')
        return jsonify({'error': 'Validation failed'}), 500

@pos_bp.route('/api/sales/history')
@login_required
def get_sales_history():
    """Get sales history for current store"""
    try:
        user_store = get_user_store()
        if not user_store:
            return jsonify({'error': 'No store assigned'}), 400
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Sale.query.filter_by(store_id=user_store.id)
        
        if start_date:
            query = query.filter(Sale.created_at >= start_date)
        if end_date:
            from datetime import datetime, timedelta
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Sale.created_at < end_datetime)
        
        sales = query.order_by(Sale.created_at.desc()).limit(50).all()
        
        results = []
        for sale in sales:
            results.append({
                'id': sale.id,
                'receipt_number': sale.receipt_number,
                'created_at': sale.created_at.isoformat(),
                'customer_name': sale.customer.name if sale.customer else None,
                'total_amount': float(sale.total_amount),
                'payment_method': sale.payment_method,
                'item_count': len(sale.sale_items)
            })
        
        return jsonify(results)
        
    except Exception as e:
        logging.error(f'Error getting sales history: {e}')
        return jsonify({'error': 'Failed to load sales history'}), 500

@pos_bp.route('/api/products')
@login_required
def get_products():
    """Get all products available in user's store"""
    user_store = get_user_store()
    if not user_store:
        return jsonify({'error': 'No store assigned'}), 400
    
    try:
        products = get_store_products(user_store.id)
        
        results = []
        for product in products:
            store_stock = product.get_store_stock(user_store.id)
            results.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'price': float(product.selling_price),
                'stock': store_stock,
                'tax_rate': float(product.tax_rate or 0),
                'category': 'Uncategorized'  # Simplified for POS display
            })
        
        return jsonify(results)
        
    except Exception as e:
        logging.error(f'Error getting products: {e}')
        return jsonify({'error': 'Failed to load products'}), 500

