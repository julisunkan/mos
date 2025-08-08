from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from forms import SaleForm, CashRegisterForm
from models import Product, Customer, Sale, SaleItem, CashRegister
from app import db
from utils import generate_receipt_number, calculate_tax
from datetime import datetime
import json

pos_bp = Blueprint('pos', __name__)

@pos_bp.route('/')
@login_required
def index():
    # Check if user has an open cash register
    register = CashRegister.query.filter_by(
        user_id=current_user.id,
        is_open=True
    ).first()
    
    if not register:
        return redirect(url_for('pos.open_register'))
    
    # Get products for POS
    products = Product.query.filter_by(is_active=True).all()
    customers = Customer.query.filter_by(is_active=True).all()
    
    return render_template('pos/index.html', 
                         products=products, 
                         customers=customers,
                         register=register)

@pos_bp.route('/register/open', methods=['GET', 'POST'])
@login_required
def open_register():
    # Check if user already has an open register
    existing_register = CashRegister.query.filter_by(
        user_id=current_user.id,
        is_open=True
    ).first()
    
    if existing_register:
        flash('You already have an open cash register.', 'info')
        return redirect(url_for('pos.index'))
    
    form = CashRegisterForm()
    if form.validate_on_submit():
        register = CashRegister(
            user_id=current_user.id,
            opening_balance=form.opening_balance.data,
            is_open=True
        )
        
        try:
            db.session.add(register)
            db.session.commit()
            flash('Cash register opened successfully!', 'success')
            return redirect(url_for('pos.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error opening register: {str(e)}', 'error')
    
    return render_template('pos/register.html', form=form, title='Open Cash Register')

@pos_bp.route('/register/close', methods=['POST'])
@login_required
def close_register():
    register = CashRegister.query.filter_by(
        user_id=current_user.id,
        is_open=True
    ).first()
    
    if not register:
        flash('No open cash register found.', 'error')
        return redirect(url_for('pos.index'))
    
    # Calculate closing balance (opening + sales + cash_in - cash_out)
    total_sales = db.session.query(db.func.sum(Sale.total_amount)).filter(
        Sale.user_id == current_user.id,
        Sale.payment_method == 'Cash',
        Sale.created_at >= register.opened_at
    ).scalar() or 0
    
    register.total_sales = total_sales
    register.closing_balance = register.opening_balance + total_sales + register.cash_in - register.cash_out
    register.is_open = False
    register.closed_at = datetime.utcnow()
    
    try:
        db.session.commit()
        flash(f'Cash register closed. Closing balance: ${register.closing_balance}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error closing register: {str(e)}', 'error')
    
    return redirect(url_for('pos.open_register'))

@pos_bp.route('/sale/process', methods=['POST'])
@login_required
def process_sale():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'items' not in data or not data['items']:
            return jsonify({'error': 'No items in sale'}), 400
        
        # Check if user has an open register
        register = CashRegister.query.filter_by(
            user_id=current_user.id,
            is_open=True
        ).first()
        
        if not register:
            return jsonify({'error': 'No open cash register'}), 400
        
        # Create the sale
        sale = Sale(
            receipt_number=generate_receipt_number(),
            user_id=current_user.id,
            customer_id=data.get('customer_id') if data.get('customer_id') else None,
            payment_method=data.get('payment_method', 'Cash'),
            discount_amount=float(data.get('discount', 0)),
            notes=data.get('notes', '')
        )
        
        db.session.add(sale)
        db.session.flush()  # Get the sale ID
        
        subtotal = 0
        tax_total = 0
        
        # Process each item
        for item_data in data['items']:
            product = Product.query.get(item_data['product_id'])
            if not product:
                return jsonify({'error': f'Product not found: {item_data["product_id"]}'}), 400
            
            quantity = int(item_data['quantity'])
            if product.stock_quantity < quantity:
                return jsonify({'error': f'Insufficient stock for {product.name}'}), 400
            
            unit_price = float(item_data.get('unit_price', product.selling_price))
            total_price = unit_price * quantity
            
            # Create sale item
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            
            db.session.add(sale_item)
            
            # Update product stock
            product.stock_quantity -= quantity
            
            subtotal += total_price
            tax_total += calculate_tax(total_price, product.tax_rate)
        
        # Update sale totals
        sale.subtotal = subtotal
        sale.tax_amount = tax_total
        sale.total_amount = subtotal + tax_total - sale.discount_amount
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'sale_id': sale.id,
            'receipt_number': sale.receipt_number,
            'total_amount': float(sale.total_amount)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/product/search')
@login_required
def search_products():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    products = Product.query.filter(
        Product.is_active == True,
        db.or_(
            Product.name.ilike(f'%{query}%'),
            Product.sku.ilike(f'%{query}%'),
            Product.barcode.ilike(f'%{query}%')
        )
    ).limit(10).all()
    
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'barcode': p.barcode,
        'price': float(p.selling_price),
        'stock': p.stock_quantity,
        'tax_rate': float(p.tax_rate)
    } for p in products])
