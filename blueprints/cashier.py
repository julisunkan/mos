from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from models import db, Product, Sale, SaleItem, Customer, Store, StoreStock, CashRegister
from utils import get_currency_symbol
import uuid

cashier_bp = Blueprint('cashier', __name__)

@cashier_bp.route('/')
@login_required
def index():
    """Main cashier interface"""
    # Get user's assigned store
    user_store = None
    if hasattr(current_user, 'user_stores') and current_user.user_stores:
        user_store = current_user.user_stores[0].store
    
    if not user_store:
        flash('You are not assigned to any store. Please contact administrator.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get products available in this store
    products = Product.query.join(StoreStock).filter(
        StoreStock.store_id == user_store.id,
        StoreStock.quantity > 0,
        Product.is_active == True
    ).all()
    
    # Get customers
    customers = Customer.query.filter_by(is_active=True).all()
    
    return render_template('cashier/pos.html', 
                         products=products, 
                         customers=customers,
                         store=user_store)

@cashier_bp.route('/api/process_sale', methods=['POST'])
@login_required
def process_sale():
    """Process a sale transaction"""
    try:
        data = request.get_json()
        
        # Get user's store
        user_store = None
        if hasattr(current_user, 'user_stores') and current_user.user_stores:
            user_store = current_user.user_stores[0].store
        
        if not user_store:
            return jsonify({'success': False, 'error': 'No store assigned'})
        
        # Validate items
        items = data.get('items', [])
        if not items:
            return jsonify({'success': False, 'error': 'No items in cart'})
        
        # Calculate totals
        subtotal = 0
        tax_total = 0
        
        # Create sale record
        sale = Sale(
            receipt_number=f"R{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=current_user.id,
            customer_id=data.get('customer_id') if data.get('customer_id') else None,
            store_id=user_store.id,
            payment_method=data.get('payment_method', 'cash'),
            created_at=datetime.now()
        )
        
        # Process each item
        sale_items = []
        for item in items:
            product = Product.query.get(item['product_id'])
            if not product:
                return jsonify({'success': False, 'error': f'Product not found: {item["product_id"]}'})
            
            # Check stock
            store_stock = StoreStock.query.filter_by(
                store_id=user_store.id,
                product_id=product.id
            ).first()
            
            if not store_stock or store_stock.quantity < item['quantity']:
                return jsonify({'success': False, 'error': f'Insufficient stock for {product.name}'})
            
            # Calculate line totals
            line_subtotal = product.selling_price * item['quantity']
            line_tax = line_subtotal * (product.tax_rate / 100) if product.tax_rate else 0
            
            subtotal += line_subtotal
            tax_total += line_tax
            
            # Create sale item
            sale_item = SaleItem(
                product_id=product.id,
                quantity=item['quantity'],
                unit_price=product.selling_price,
                total_price=line_subtotal,
                tax_amount=line_tax
            )
            sale_items.append(sale_item)
            
            # Update stock
            store_stock.quantity -= item['quantity']
        
        # Set sale totals
        sale.subtotal = subtotal
        sale.tax_amount = tax_total
        sale.total_amount = subtotal + tax_total
        
        # Save to database
        db.session.add(sale)
        db.session.flush()  # Get sale ID
        
        for sale_item in sale_items:
            sale_item.sale_id = sale.id
            db.session.add(sale_item)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'sale_id': sale.id,
            'receipt_number': sale.receipt_number,
            'total': sale.total_amount
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@cashier_bp.route('/receipt/<int:sale_id>')
@login_required
def receipt(sale_id):
    """Display receipt for a sale"""
    sale = Sale.query.get_or_404(sale_id)
    
    # Security check - ensure user can view this receipt
    user_store = None
    if hasattr(current_user, 'user_stores') and current_user.user_stores:
        user_store = current_user.user_stores[0].store
    
    if sale.store_id != user_store.id and not current_user.has_permission('all'):
        flash('Access denied', 'error')
        return redirect(url_for('cashier.index'))
    
    return render_template('cashier/receipt.html', sale=sale)

@cashier_bp.route('/api/search_products')
@login_required
def search_products():
    """Search products for POS"""
    query = request.args.get('q', '').strip()
    
    # Get user's store
    user_store = None
    if hasattr(current_user, 'user_stores') and current_user.user_stores:
        user_store = current_user.user_stores[0].store
    
    if not user_store:
        return jsonify([])
    
    # Search products
    products = Product.query.join(StoreStock).filter(
        StoreStock.store_id == user_store.id,
        StoreStock.quantity > 0,
        Product.is_active == True
    )
    
    if query:
        products = products.filter(
            db.or_(
                Product.name.ilike(f'%{query}%'),
                Product.sku.ilike(f'%{query}%'),
                Product.barcode.ilike(f'%{query}%')
            )
        )
    
    products = products.limit(20).all()
    
    result = []
    for product in products:
        store_stock = StoreStock.query.filter_by(
            store_id=user_store.id,
            product_id=product.id
        ).first()
        
        result.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'price': float(product.selling_price),
            'stock': store_stock.quantity if store_stock else 0
        })
    
    return jsonify(result)