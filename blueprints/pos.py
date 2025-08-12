from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from forms import SaleForm, CashRegisterForm, ReturnForm
from models import Product, Customer, Sale, SaleItem, CashRegister, UserStore, StoreStock, SaleReturn, SaleReturnItem
from app import db
from utils import generate_receipt_number, calculate_tax, generate_hold_number, generate_return_number
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
    
    # Get products available in the current user's store
    store_id = register.store_id
    
    # Debug: Add logging
    print(f"DEBUG: Current user: {current_user.id}, Register store: {store_id}")
    
    products = db.session.query(Product).join(StoreStock).filter(
        Product.is_active == True,
        StoreStock.store_id == store_id,
        StoreStock.quantity > 0  # Only show products with stock
    ).all()
    
    print(f"DEBUG: Found {len(products)} products in store {store_id}")
    
    customers = Customer.query.filter_by(is_active=True).all()
    
    return render_template('pos/index_modern.html', 
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
    
    # Get user's default store
    user_store = UserStore.query.filter_by(
        user_id=current_user.id,
        is_default=True
    ).first()
    
    if not user_store:
        # If no default store, get the first one assigned to user
        user_store = UserStore.query.filter_by(user_id=current_user.id).first()
    
    if not user_store:
        flash('You are not assigned to any store. Please contact an administrator.', 'error')
        return redirect(url_for('auth.login'))
    
    form = CashRegisterForm()
    if form.validate_on_submit():
        register = CashRegister()
        register.user_id = current_user.id
        register.store_id = user_store.store_id
        register.opening_balance = form.opening_balance.data
        register.is_open = True
        
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

@pos_bp.route('/api/sale/process', methods=['POST'])
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
        sale = Sale()
        sale.receipt_number = generate_receipt_number()
        sale.user_id = current_user.id
        sale.store_id = register.store_id
        sale.customer_id = data.get('customer_id') if data.get('customer_id') else None
        sale.payment_method = data.get('payment_method', 'Cash')
        sale.discount_amount = float(data.get('discount', 0))
        sale.notes = data.get('notes', '')
        
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
            
            # Check store-specific stock instead of global product stock
            store_stock = StoreStock.query.filter_by(
                product_id=product.id,
                store_id=register.store_id
            ).first()
            
            if not store_stock or store_stock.quantity < quantity:
                return jsonify({'error': f'Insufficient stock for {product.name} in this store'}), 400
            
            unit_price = float(item_data.get('unit_price', float(product.selling_price)))
            total_price = unit_price * quantity
            
            # Create sale item
            sale_item = SaleItem()
            sale_item.sale_id = sale.id
            sale_item.product_id = product.id
            sale_item.quantity = quantity
            sale_item.unit_price = unit_price
            sale_item.total_price = total_price
            
            db.session.add(sale_item)
            
            # Update store-specific stock instead of global product stock
            store_stock.quantity -= quantity
            
            subtotal += total_price
            if product.tax_rate:
                tax_total += total_price * (float(product.tax_rate) / 100)
        
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



# Enhanced POS Features: Hold/Resume Sales and Returns
@pos_bp.route('/hold-sale', methods=['POST'])
@login_required
def hold_sale():
    """Hold the current sale for later completion"""
    from models import HeldSale, HeldSaleItem
    
    data = request.get_json()
    
    try:
        hold_number = generate_hold_number()
        
        # Create held sale record
        held_sale = HeldSale()
        held_sale.hold_number = hold_number
        held_sale.user_id = current_user.id
        held_sale.customer_id = data.get('customer_id')
        held_sale.subtotal = data.get('subtotal', 0)
        held_sale.tax_amount = data.get('tax_amount', 0)
        held_sale.discount_amount = data.get('discount_amount', 0)
        held_sale.total_amount = data.get('total_amount', 0)
        held_sale.notes = data.get('notes', '')
        
        db.session.add(held_sale)
        db.session.flush()  # Get the ID
        
        # Add held sale items
        for item in data.get('items', []):
            held_item = HeldSaleItem()
            held_item.held_sale_id = held_sale.id
            held_item.product_id = item['product_id']
            held_item.quantity = item['quantity']
            held_item.unit_price = item['unit_price']
            held_item.total_price = item['total_price']
            db.session.add(held_item)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'hold_number': hold_number,
            'message': f'Sale held successfully as #{hold_number}'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error holding sale: {str(e)}'
        }), 500

@pos_bp.route('/held-sales')
@login_required
def held_sales():
    """Get list of held sales for current user"""
    from models import HeldSale
    
    held_sales_list = HeldSale.query.filter_by(user_id=current_user.id).order_by(HeldSale.created_at.desc()).all()
    
    sales_data = []
    for sale in held_sales_list:
        sales_data.append({
            'id': sale.id,
            'hold_number': sale.hold_number,
            'customer_name': sale.customer.name if sale.customer else 'Walk-in',
            'total_amount': float(sale.total_amount),
            'created_at': sale.created_at.strftime('%Y-%m-%d %H:%M'),
            'item_count': len(sale.items)
        })
    
    return jsonify({
        'success': True,
        'held_sales': sales_data
    })

@pos_bp.route('/resume-sale/<int:sale_id>')
@login_required
def resume_sale(sale_id):
    """Resume a held sale"""
    from models import HeldSale
    
    held_sale = HeldSale.query.get_or_404(sale_id)
    
    if held_sale.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Convert held sale to cart format
    cart_items = []
    for item in held_sale.items:
        cart_items.append({
            'product_id': item.product_id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'total_price': float(item.total_price)
        })
    
    return jsonify({
        'success': True,
        'sale_data': {
            'customer_id': held_sale.customer_id,
            'items': cart_items,
            'subtotal': float(held_sale.subtotal),
            'tax_amount': float(held_sale.tax_amount),
            'discount_amount': float(held_sale.discount_amount),
            'total_amount': float(held_sale.total_amount),
            'notes': held_sale.notes
        }
    })

@pos_bp.route('/pos_returns')
@login_required
def pos_returns():
    """Display returns and refunds page"""
    from forms import ReturnForm
    form = ReturnForm()
    
    # Get recent sales for returns
    recent_sales = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.created_at.desc()).limit(50).all()
    
    return render_template('pos/returns.html', 
                         form=form, 
                         recent_sales=recent_sales)

@pos_bp.route('/api/products')
@login_required
def get_products():
    """Get all products available in user's store"""
    # Get user's current register to find their store
    register = CashRegister.query.filter_by(
        user_id=current_user.id,
        is_open=True
    ).first()
    
    if not register:
        return jsonify([])
    
    # Get products available in the user's store with stock
    products = db.session.query(Product, StoreStock.quantity).join(StoreStock).filter(
        Product.is_active == True,
        StoreStock.store_id == register.store_id
    ).all()
    
    results = []
    for product, stock_quantity in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'price': float(product.selling_price),
            'stock': stock_quantity,  # Use store-specific stock
            'tax_rate': float(product.tax_rate or 0)
        })
    
    return jsonify(results)

@pos_bp.route('/api/products/search')
@login_required
def search_products():
    """Search products for POS (filtered by user's store)"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    # Get user's current register to find their store
    register = CashRegister.query.filter_by(
        user_id=current_user.id,
        is_open=True
    ).first()
    
    if not register:
        return jsonify([])
    
    # Search products available in the user's store with stock
    products = db.session.query(Product, StoreStock.quantity).join(StoreStock).filter(
        db.or_(
            Product.name.ilike(f'%{query}%'),
            Product.sku.ilike(f'%{query}%'),
            Product.barcode.ilike(f'%{query}%')
        ),
        Product.is_active == True,
        StoreStock.store_id == register.store_id,
        StoreStock.quantity > 0
    ).limit(20).all()
    
    results = []
    for product, stock_quantity in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'price': float(product.selling_price),
            'stock': stock_quantity,  # Use store-specific stock
            'tax_rate': float(product.tax_rate or 0)
        })
    
    return jsonify(results)

@pos_bp.route('/api/sale/<int:sale_id>/details')
@login_required
def get_sale_details(sale_id):
    """Get detailed information about a specific sale for returns"""
    sale = Sale.query.get_or_404(sale_id)
    
    # Build sale details JSON
    sale_data = {
        'id': sale.id,
        'receipt_number': sale.receipt_number,
        'created_at': sale.created_at.isoformat(),
        'customer_name': sale.customer.name if sale.customer else None,
        'total_amount': float(sale.total_amount),
        'items': []
    }
    
    # Add sale items
    for item in sale.sale_items:
        sale_data['items'].append({
            'id': item.id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'total_price': float(item.total_price)
        })
    
    return jsonify(sale_data)

@pos_bp.route('/api/process_return', methods=['POST'])
@login_required
def process_return():
    """Process a return with selected items and quantities"""
    try:
        data = request.get_json()
        
        if not data or 'sale_id' not in data:
            return jsonify({'error': 'Sale ID is required'}), 400
        
        sale_id = data['sale_id']
        return_reason = data.get('return_reason', 'Customer request')
        notes = data.get('notes', '')
        return_items = data.get('items', [])
        
        if not return_items:
            return jsonify({'error': 'No items specified for return'}), 400
        
        # Find the original sale
        original_sale = Sale.query.get_or_404(sale_id)
        
        # Check if this sale can be returned by current user or admin
        if not (current_user.has_permission('all') or original_sale.user_id == current_user.id):
            return jsonify({'error': 'Not authorized to return this sale'}), 403
        
        # Generate return number
        return_number = generate_return_number()
        
        # Create return record
        sale_return = SaleReturn()
        sale_return.return_number = return_number
        sale_return.original_sale_id = original_sale.id
        sale_return.user_id = current_user.id
        sale_return.return_reason = return_reason
        sale_return.notes = notes
        sale_return.status = 'Processed'
        
        db.session.add(sale_return)
        db.session.flush()  # Get the return ID
        
        total_return_amount = 0
        
        # Process each return item
        for return_item_data in return_items:
            item_id = return_item_data['item_id']
            return_qty = int(return_item_data['quantity'])
            unit_price = float(return_item_data['unit_price'])
            
            # Find the original sale item
            original_item = SaleItem.query.get(item_id)
            if not original_item or original_item.sale_id != original_sale.id:
                return jsonify({'error': f'Invalid sale item: {item_id}'}), 400
            
            if return_qty > original_item.quantity:
                return jsonify({'error': f'Return quantity cannot exceed sold quantity for {original_item.product.name}'}), 400
            
            if return_qty <= 0:
                continue
                
            # Calculate return amount
            return_amount = unit_price * return_qty
            total_return_amount += return_amount
            
            # Create return item record
            return_item = SaleReturnItem()
            return_item.return_id = sale_return.id
            return_item.product_id = original_item.product_id
            return_item.original_sale_item_id = original_item.id
            return_item.quantity = return_qty
            return_item.unit_price = unit_price
            return_item.total_refund = return_amount
            
            db.session.add(return_item)
            
            # Restore store-specific stock instead of global stock
            store_stock = StoreStock.query.filter_by(
                product_id=original_item.product_id,
                store_id=original_sale.store_id
            ).first()
            if store_stock:
                store_stock.quantity += return_qty
            else:
                # Create store stock entry if it doesn't exist
                new_store_stock = StoreStock()
                new_store_stock.product_id = original_item.product_id
                new_store_stock.store_id = original_sale.store_id
                new_store_stock.quantity = return_qty
                db.session.add(new_store_stock)
        
        # Update return total
        sale_return.return_amount = total_return_amount
        sale_return.processed_at = datetime.utcnow()
        
        # Create negative sale entry for refund tracking
        refund_sale = Sale()
        refund_sale.receipt_number = f"REF-{return_number}"
        refund_sale.user_id = current_user.id
        refund_sale.store_id = original_sale.store_id
        refund_sale.customer_id = original_sale.customer_id
        refund_sale.payment_method = original_sale.payment_method
        refund_sale.subtotal = -total_return_amount
        refund_sale.tax_amount = 0  # Tax calculation for returns can be added later
        refund_sale.discount_amount = 0
        refund_sale.total_amount = -total_return_amount
        refund_sale.notes = f'REFUND for {original_sale.receipt_number} - {return_reason}'
        
        db.session.add(refund_sale)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'return_id': sale_return.id,
            'return_number': return_number,
            'return_amount': float(total_return_amount),
            'message': f'Return processed successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/receipt/print/<receipt_number>')
@login_required
def print_receipt(receipt_number):
    """Generate and download PDF receipt"""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from flask import make_response
    from utils import get_currency_symbol
    import io
    
    # Find the sale by receipt number
    sale = Sale.query.filter_by(receipt_number=receipt_number).first()
    if not sale:
        return jsonify({'error': 'Receipt not found'}), 404
    
    # Get currency symbol
    currency_symbol = get_currency_symbol()
    
    # Create PDF in memory
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Receipt header
    p.setFont("Helvetica-Bold", 16)
    title_text = "Cloud POS & Inventory Manager"
    text_width = p.stringWidth(title_text, "Helvetica-Bold", 16)
    p.drawString((width - text_width) / 2, height-50, title_text)
    
    p.setFont("Helvetica", 12)
    receipt_text = f"Receipt: {receipt_number}"
    text_width = p.stringWidth(receipt_text, "Helvetica", 12)
    p.drawString((width - text_width) / 2, height-80, receipt_text)
    
    date_text = f"Date: {sale.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    text_width = p.stringWidth(date_text, "Helvetica", 12)
    p.drawString((width - text_width) / 2, height-100, date_text)
    
    cashier_text = f"Cashier: {sale.user.full_name}"
    text_width = p.stringWidth(cashier_text, "Helvetica", 12)
    p.drawString((width - text_width) / 2, height-120, cashier_text)
    
    if sale.customer:
        customer_text = f"Customer: {sale.customer.name}"
        text_width = p.stringWidth(customer_text, "Helvetica", 12)
        p.drawString((width - text_width) / 2, height-140, customer_text)
        y_pos = height - 170
    else:
        customer_text = "Customer: Walk-in"
        text_width = p.stringWidth(customer_text, "Helvetica", 12)
        p.drawString((width - text_width) / 2, height-140, customer_text)
        y_pos = height - 170
    
    # Line separator
    p.line(50, y_pos, width-50, y_pos)
    y_pos -= 30
    
    # Items header
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y_pos, "Item")
    p.drawString(300, y_pos, "Qty")
    p.drawString(350, y_pos, "Price")
    p.drawString(450, y_pos, "Total")
    y_pos -= 20
    
    # Items
    p.setFont("Helvetica", 10)
    for item in sale.items:
        p.drawString(50, y_pos, item.product.name[:30])  # Truncate long names
        p.drawString(300, y_pos, str(item.quantity))
        p.drawString(350, y_pos, f"{currency_symbol}{item.unit_price:.2f}")
        p.drawString(450, y_pos, f"{currency_symbol}{item.total_price:.2f}")
        y_pos -= 15
    
    # Totals section
    y_pos -= 20
    p.line(50, y_pos, width-50, y_pos)
    y_pos -= 20
    
    p.setFont("Helvetica", 10)
    p.drawString(350, y_pos, f"Subtotal:")
    p.drawString(450, y_pos, f"{currency_symbol}{sale.subtotal:.2f}")
    y_pos -= 15
    
    p.drawString(350, y_pos, f"Tax:")
    p.drawString(450, y_pos, f"{currency_symbol}{sale.tax_amount:.2f}")
    y_pos -= 15
    
    if sale.discount_amount > 0:
        p.drawString(350, y_pos, f"Discount:")
        p.drawString(450, y_pos, f"-{currency_symbol}{sale.discount_amount:.2f}")
        y_pos -= 15
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(350, y_pos, f"Total:")
    p.drawString(450, y_pos, f"{currency_symbol}{sale.total_amount:.2f}")
    y_pos -= 20
    
    p.setFont("Helvetica", 10)
    p.drawString(350, y_pos, f"Payment:")
    p.drawString(450, y_pos, sale.payment_method)
    
    # Footer
    p.setFont("Helvetica", 8)
    
    footer_text = "Thank you for your business!"
    text_width = p.stringWidth(footer_text, "Helvetica", 8)
    p.drawString((width - text_width) / 2, 100, footer_text)
    
    powered_text = "Powered by Cloud POS"
    text_width = p.stringWidth(powered_text, "Helvetica", 8)
    p.drawString((width - text_width) / 2, 80, powered_text)
    
    p.save()
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=receipt_{receipt_number}.pdf'
    
    return response

@pos_bp.route('/pos_returns_v2')
@login_required 
def pos_returns_v2():
    """Display returns management page for cashiers"""
    # Get recent sales that can be returned (within last 30 days)
    from datetime import datetime, timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    
    recent_sales = Sale.query.filter(
        Sale.created_at >= cutoff_date,
        Sale.total_amount > 0  # Don't show refund transactions
    ).order_by(Sale.created_at.desc()).limit(50).all()
    
    return render_template('pos/returns.html', recent_sales=recent_sales)


