from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from models import Product, Customer, Sale, SaleItem, CashRegister, UserStore, StoreStock, Store
from app import db
from utils import generate_receipt_number, format_currency, get_currency_symbol
from datetime import datetime
from decimal import Decimal
import logging

cashier_bp = Blueprint('cashier', __name__)

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

@cashier_bp.route('/')
@login_required
def index():
    """Main cashier POS interface"""
    # Check if user has a store assignment
    user_store = get_user_store()
    if not user_store:
        flash('You are not assigned to any store. Please contact your administrator.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if user has an open cash register
    cash_register = get_user_cash_register()
    if not cash_register:
        return redirect(url_for('cashier.open_register'))
    
    # Get products available in this store
    products = get_store_products(user_store.id)
    
    # Get customers
    customers = Customer.query.filter_by(is_active=True).order_by(Customer.name).all()
    
    return render_template('cashier/pos.html', 
                         products=products,
                         customers=customers,
                         store=user_store,
                         cash_register=cash_register)

@cashier_bp.route('/register/open', methods=['GET', 'POST'])
@login_required
def open_register():
    """Open cash register"""
    user_store = get_user_store()
    if not user_store:
        flash('You are not assigned to any store. Please contact your administrator.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if register is already open
    existing_register = get_user_cash_register()
    if existing_register:
        return redirect(url_for('cashier.index'))
    
    if request.method == 'POST':
        opening_balance = Decimal(request.form.get('opening_balance', '0.00'))
        
        # Create new cash register session
        cash_register = CashRegister()
        cash_register.user_id = current_user.id
        cash_register.store_id = user_store.id
        cash_register.opening_balance = opening_balance
        cash_register.opened_at = datetime.utcnow()
        cash_register.is_open = True
        
        db.session.add(cash_register)
        db.session.commit()
        
        flash('Cash register opened successfully!', 'success')
        return redirect(url_for('cashier.index'))
    
    return render_template('cashier/open_register.html', store=user_store)

@cashier_bp.route('/api/products')
@login_required
def api_products():
    """API endpoint to get products for current store"""
    user_store = get_user_store()
    if not user_store:
        return jsonify([])
    
    search_term = request.args.get('search', '')
    products = get_store_products(user_store.id, search_term)
    
    results = []
    for product in products:
        # Get current stock from store_stock table
        stock_info = StoreStock.query.filter_by(
            store_id=user_store.id, 
            product_id=product.id
        ).first()
        
        current_stock = stock_info.quantity if stock_info else 0
        
        results.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'barcode': product.barcode,
            'price': float(product.selling_price),
            'stock': int(current_stock),
            'tax_rate': float(product.tax_rate) if product.tax_rate else 0,
            'category': product.category.name if product.category else 'Uncategorized'
        })
    
    return jsonify(results)

@cashier_bp.route('/api/process_sale', methods=['POST'])
@login_required
def process_sale():
    """Process a complete sale transaction"""
    try:
        data = request.get_json()
        
        user_store = get_user_store()
        if not user_store:
            return jsonify({'error': 'No store assigned'}), 400
        
        cash_register = get_user_cash_register()
        if not cash_register:
            return jsonify({'error': 'No open cash register'}), 400
        
        # Validate required fields
        items = data.get('items', [])
        payment_method = data.get('payment_method', 'cash')
        customer_id = data.get('customer_id')
        
        if not items:
            return jsonify({'error': 'No items in sale'}), 400
        
        # Calculate totals
        subtotal = Decimal('0.00')
        tax_total = Decimal('0.00')
        
        # Validate stock and calculate totals
        for item in items:
            product = Product.query.get(item['product_id'])
            if not product:
                return jsonify({'error': f'Product not found: {item["product_id"]}'}), 400
            
            # Check stock availability
            stock_info = StoreStock.query.filter_by(
                store_id=user_store.id,
                product_id=product.id
            ).first()
            
            if not stock_info or stock_info.quantity < item['quantity']:
                return jsonify({'error': f'Insufficient stock for {product.name}'}), 400
            
            # Calculate line totals
            line_subtotal = Decimal(str(product.selling_price)) * Decimal(str(item['quantity']))
            line_tax = line_subtotal * (Decimal(str(product.tax_rate or 0)) / 100)
            
            subtotal += line_subtotal
            tax_total += line_tax
        
        total_amount = subtotal + tax_total
        
        # Create sale record
        sale = Sale()
        sale.receipt_number = generate_receipt_number()
        sale.user_id = current_user.id
        sale.store_id = user_store.id
        sale.customer_id = customer_id if customer_id else None
        sale.subtotal = subtotal
        sale.tax_amount = tax_total
        sale.total_amount = total_amount
        sale.payment_method = payment_method
        sale.created_at = datetime.utcnow()
        
        db.session.add(sale)
        db.session.flush()  # Get the sale ID
        
        # Create sale items and update stock
        for item in items:
            product = Product.query.get(item['product_id'])
            quantity = item['quantity']
            
            # Create sale item
            sale_item = SaleItem()
            sale_item.sale_id = sale.id
            sale_item.product_id = product.id
            sale_item.quantity = quantity
            sale_item.unit_price = product.selling_price
            sale_item.total_price = Decimal(str(product.selling_price)) * Decimal(str(quantity))
            db.session.add(sale_item)
            
            # Update store stock
            stock_info = StoreStock.query.filter_by(
                store_id=user_store.id,
                product_id=product.id
            ).first()
            stock_info.quantity -= quantity
        
        # Update cash register balance for cash payments
        if payment_method == 'cash':
            # Note: CashRegister model doesn't have current_balance field, using total_sales instead
            cash_register.total_sales += total_amount
        
        db.session.commit()
        
        # Return sale details for receipt
        return jsonify({
            'success': True,
            'sale_id': sale.id,
            'receipt_number': sale.receipt_number,
            'subtotal': float(subtotal),
            'tax_amount': float(tax_total),
            'total_amount': float(total_amount),
            'payment_method': payment_method,
            'timestamp': sale.created_at.isoformat()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f'Error processing sale: {e}')
        return jsonify({'error': 'Failed to process sale'}), 500

@cashier_bp.route('/receipt/<int:sale_id>')
@login_required
def print_receipt(sale_id):
    """Generate printable receipt"""
    sale = Sale.query.get_or_404(sale_id)
    
    # Verify sale belongs to current user's store
    user_store = get_user_store()
    if not user_store or sale.store_id != user_store.id:
        flash('Receipt not found or access denied.', 'error')
        return redirect(url_for('cashier.index'))
    
    return render_template('cashier/receipt.html', sale=sale)