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
                'category': product.category.name if product.category else 'Uncategorized'
            })
        
        return jsonify(results)
        
    except Exception as e:
        logging.error(f'Error getting products: {e}')
        return jsonify({'error': 'Failed to load products'}), 500