from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from models import Product, Customer, Sale, SaleItem, CashRegister, UserStore, SaleReturn, SaleReturnItem
from app import db
from utils import generate_receipt_number, generate_return_number, get_default_currency, format_currency, get_currency_symbol
from datetime import datetime
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

pos_bp = Blueprint('pos', __name__)

@pos_bp.route('/')
@login_required
def index():
    """Main POS interface"""
    # Check if user has an open cash register
    register = CashRegister.query.filter_by(
        user_id=current_user.id,
        is_open=True
    ).first()
    
    if not register:
        return redirect(url_for('pos.open_register'))
    
    # Get products and customers
    products = Product.query.filter_by(is_active=True).limit(20).all()
    customers = Customer.query.filter_by(is_active=True).all()
    
    return render_template('pos/index_new.html', 
                         products=products, 
                         customers=customers,
                         register=register)

@pos_bp.route('/register/open', methods=['GET', 'POST'])
@login_required
def open_register():
    """Open cash register"""
    # Check if user already has an open register
    existing_register = CashRegister.query.filter_by(
        user_id=current_user.id,
        is_open=True
    ).first()
    
    if existing_register:
        flash('You already have an open cash register.', 'info')
        return redirect(url_for('pos.index'))
    
    if request.method == 'POST':
        opening_balance = float(request.form.get('opening_balance', 0))
        
        # Get user's store (first available store if multiple)
        user_store = UserStore.query.filter_by(user_id=current_user.id).first()
        if not user_store:
            flash('You are not assigned to any store.', 'error')
            return redirect(url_for('dashboard'))
        
        # Create new cash register
        register = CashRegister()
        register.user_id = current_user.id
        register.store_id = user_store.store_id
        register.opening_balance = opening_balance
        register.closing_balance = 0
        register.total_sales = 0
        register.cash_in = 0
        register.cash_out = 0
        register.is_open = True
        register.opened_at = datetime.utcnow()
        
        try:
            db.session.add(register)
            db.session.commit()
            flash(f'Cash register opened with {format_currency(opening_balance)}', 'success')
            return redirect(url_for('pos.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error opening register: {str(e)}', 'error')
    
    return render_template('pos/register.html')

@pos_bp.route('/register/close', methods=['POST'])
@login_required
def close_register():
    """Close cash register"""
    register = CashRegister.query.filter_by(
        user_id=current_user.id,
        is_open=True
    ).first()
    
    if not register:
        flash('No open cash register found.', 'error')
        return redirect(url_for('pos.index'))
    
    # Calculate closing balance
    total_sales = db.session.query(db.func.sum(Sale.total_amount)).filter(
        Sale.user_id == current_user.id,
        Sale.payment_method == 'Cash',
        Sale.created_at >= register.opened_at
    ).scalar() or 0
    
    register.total_sales = total_sales
    register.closing_balance = register.opening_balance + total_sales
    register.is_open = False
    register.closed_at = datetime.utcnow()
    
    try:
        db.session.commit()
        flash(f'Cash register closed. Closing balance: {format_currency(register.closing_balance)}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error closing register: {str(e)}', 'error')
    
    return redirect(url_for('pos.open_register'))

@pos_bp.route('/api/products/search')
@login_required
def search_products():
    """Search products for POS"""
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify([])
    
    # Search by name, SKU, or barcode
    products = Product.query.filter(
        db.or_(
            Product.name.ilike(f'%{query}%'),
            Product.sku.ilike(f'%{query}%'),
            Product.barcode.ilike(f'%{query}%')
        ),
        Product.is_active == True
    ).limit(10).all()
    
    results = []
    for product in products:
        results.append({
            'id': product.id,
            'name': product.name,
            'price': float(product.selling_price),
            'stock': product.stock_quantity,
            'tax_rate': float(product.tax_rate or 0)
        })
    
    return jsonify(results)

@pos_bp.route('/api/sale/process', methods=['POST'])
@login_required
def process_sale():
    """Process a sale"""
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
        
        # Create the sale with default currency
        sale = Sale()
        sale.receipt_number = generate_receipt_number()
        sale.user_id = current_user.id
        sale.store_id = register.store_id
        sale.customer_id = data.get('customer_id') if data.get('customer_id') else None
        sale.payment_method = data.get('payment_method', 'Cash')
        sale.discount_amount = float(data.get('discount', 0))
        sale.notes = data.get('notes', '')
        sale.currency = get_default_currency()
        sale.exchange_rate = 1.0
        
        db.session.add(sale)
        db.session.flush()  # Get the sale ID
        
        subtotal = 0
        tax_total = 0
        
        # Process each item
        for item_data in data['items']:
            # Validate product_id
            product_id = item_data.get('product_id')
            if not product_id:
                return jsonify({'error': 'Missing product ID in cart item'}), 400
            
            try:
                product_id = int(product_id)
            except (ValueError, TypeError):
                return jsonify({'error': f'Invalid product ID: {product_id}'}), 400
            
            product = Product.query.filter_by(id=product_id).first()
            if not product:
                return jsonify({'error': f'Product not found: {product_id}'}), 400
            
            if not product.is_active:
                return jsonify({'error': f'Product {product.name} is not available'}), 400
            
            # Validate quantity
            try:
                quantity = int(item_data.get('quantity', 0))
                if quantity <= 0:
                    return jsonify({'error': f'Invalid quantity for {product.name}'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': f'Invalid quantity for {product.name}'}), 400
            
            if product.stock_quantity < quantity:
                return jsonify({'error': f'Insufficient stock for {product.name}. Available: {product.stock_quantity}'}), 400
            
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
            
            # Update product stock
            product.stock_quantity -= quantity
            
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

@pos_bp.route('/api/refund/process', methods=['POST'])
@login_required
def process_refund():
    """Process a refund"""
    try:
        data = request.get_json()
        
        if not data or 'receipt_number' not in data:
            return jsonify({'error': 'Receipt number is required'}), 400
            
        receipt_number = data['receipt_number']
        reason = data.get('reason', 'Customer request')
        
        # Find the original sale
        original_sale = Sale.query.filter_by(receipt_number=receipt_number).first()
        if not original_sale:
            return jsonify({'error': 'Sale not found'}), 404
            
        # Check if already refunded
        existing_refund = Sale.query.filter(
            Sale.notes.ilike(f'%REFUND:{receipt_number}%')
        ).first()
        if existing_refund:
            return jsonify({'error': 'This sale has already been refunded'}), 400
        
        # Create refund entry (negative sale)
        refund_receipt = f"REF-{generate_receipt_number()}"
        refund_sale = Sale()
        refund_sale.receipt_number = refund_receipt
        refund_sale.user_id = current_user.id
        refund_sale.store_id = original_sale.store_id
        refund_sale.customer_id = original_sale.customer_id
        refund_sale.payment_method = original_sale.payment_method
        refund_sale.subtotal = -original_sale.subtotal
        refund_sale.tax_amount = -original_sale.tax_amount
        refund_sale.discount_amount = -original_sale.discount_amount
        refund_sale.total_amount = -original_sale.total_amount
        refund_sale.notes = f'REFUND:{receipt_number} - {reason}'
        
        db.session.add(refund_sale)
        db.session.flush()  # Get the refund sale ID
        
        # Create refund items (restore stock)
        for original_item in original_sale.sale_items:
            refund_item = SaleItem()
            refund_item.sale_id = refund_sale.id
            refund_item.product_id = original_item.product_id
            refund_item.quantity = -original_item.quantity  # Negative quantity for refund
            refund_item.unit_price = original_item.unit_price
            refund_item.total_price = -original_item.total_price
            db.session.add(refund_item)
            
            # Restore stock
            product = Product.query.get(original_item.product_id)
            if product:
                product.stock_quantity += original_item.quantity
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'refund_id': refund_sale.id,
            'refund_receipt': refund_receipt,
            'refund_amount': float(original_sale.total_amount)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/receipt/<receipt_number>/download')
@login_required
def download_receipt(receipt_number):
    """Generate and download PDF receipt"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        from utils import get_currency_symbol
        
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
        text = p.beginText(width/2, height-50)
        text.setFont("Helvetica-Bold", 16)
        text.textLine("Cloud POS & Inventory Manager")
        p.drawText(text)
        
        p.setFont("Helvetica", 12)
        p.drawString(width/2-50, height-80, f"Receipt: {receipt_number}")
        p.drawString(width/2-50, height-100, f"Date: {sale.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        p.drawString(width/2-50, height-120, f"Cashier: {sale.user.full_name}")
        
        if sale.customer:
            p.drawString(width/2-50, height-140, f"Customer: {sale.customer.name}")
            y_pos = height - 170
        else:
            p.drawString(width/2-50, height-140, "Customer: Walk-in")
            y_pos = height - 170
        
        # Line separator
        p.line(50, y_pos, width-50, y_pos)
        y_pos -= 30
        
        # Items
        p.setFont("Helvetica", 10)
        for item in sale.sale_items:
            p.drawString(50, y_pos, f"{item.product.name} x{item.quantity}")
            p.drawString(450, y_pos, f"{currency_symbol}{item.total_price:.2f}")
            y_pos -= 15
        
        # Totals
        y_pos -= 20
        p.line(50, y_pos, width-50, y_pos)
        y_pos -= 20
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(350, y_pos, f"Total: {currency_symbol}{sale.total_amount:.2f}")
        
        # Footer
        p.setFont("Helvetica", 8)
        p.drawString(width/2-50, 100, "Thank you for your business!")
        
        p.save()
        buffer.seek(0)
        
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=receipt_{receipt_number}.pdf'
        
        return response
        
    except ImportError:
        # Fallback if reportlab is not available
        return jsonify({'error': 'PDF generation not available'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@pos_bp.route('/receipt/<receipt_number>/print')
@login_required
def print_receipt(receipt_number):
    """Generate HTML receipt for printing"""
    from utils import get_currency_symbol
    
    # Find the sale by receipt number
    sale = Sale.query.filter_by(receipt_number=receipt_number).first()
    if not sale:
        return jsonify({'error': 'Receipt not found'}), 404
    
    # Get currency symbol
    currency_symbol = get_currency_symbol()
    
    # Generate HTML receipt content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Receipt {receipt_number}</title>
        <style>
            @media print {{
                body {{ margin: 0; padding: 20px; font-family: monospace; }}
                .no-print {{ display: none; }}
            }}
            body {{ 
                font-family: monospace; 
                width: 350px; 
                margin: 0 auto; 
                padding: 20px;
                background: white;
                color: black;
            }}
            .header {{ 
                text-align: center; 
                border-bottom: 2px dashed #000; 
                padding-bottom: 15px; 
                margin-bottom: 15px;
            }}
            .header h2 {{ margin: 0 0 10px 0; font-size: 18px; }}
            .item {{ 
                display: flex; 
                justify-content: space-between; 
                margin: 8px 0; 
                padding: 2px 0;
            }}
            .item-name {{ flex: 1; }}
            .item-qty {{ width: 60px; text-align: center; }}
            .item-price {{ width: 80px; text-align: right; }}
            .total-section {{ 
                border-top: 2px dashed #000; 
                padding-top: 15px; 
                margin-top: 15px;
            }}
            .total-line {{ 
                display: flex; 
                justify-content: space-between; 
                margin: 5px 0;
                font-weight: bold;
            }}
            .footer {{ 
                text-align: center; 
                margin-top: 20px; 
                font-size: 12px; 
                border-top: 1px dashed #000;
                padding-top: 15px;
            }}
            .print-btn {{
                background: #007bff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                margin: 10px 5px;
            }}
            .print-controls {{
                text-align: center;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="print-controls no-print">
            <button class="print-btn" onclick="window.print()">🖨️ Print Receipt</button>
            <button class="print-btn" onclick="window.close()">❌ Close</button>
        </div>
        
        <div class="header">
            <h2>Cloud POS & Inventory Manager</h2>
            <div>Receipt: {receipt_number}</div>
            <div>Date: {sale.created_at.strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div>Cashier: {sale.user.full_name}</div>
            <div>Customer: {sale.customer.name if sale.customer else 'Walk-in'}</div>
        </div>
        
        <div class="items">
            <div class="item" style="font-weight: bold; border-bottom: 1px solid #000;">
                <div class="item-name">Item</div>
                <div class="item-qty">Qty</div>
                <div class="item-price">Total</div>
            </div>"""
    
    for item in sale.sale_items:
        html_content += f"""
            <div class="item">
                <div class="item-name">{item.product.name}</div>
                <div class="item-qty">{item.quantity}</div>
                <div class="item-price">{currency_symbol}{item.total_price:.2f}</div>
            </div>"""
    
    html_content += f"""
        </div>
        
        <div class="total-section">
            <div class="total-line">
                <span>Subtotal:</span>
                <span>{currency_symbol}{sale.subtotal:.2f}</span>
            </div>
            <div class="total-line">
                <span>Tax:</span>
                <span>{currency_symbol}{sale.tax_amount:.2f}</span>
            </div>"""
    
    if sale.discount_amount > 0:
        html_content += f"""
            <div class="total-line">
                <span>Discount:</span>
                <span>-{currency_symbol}{sale.discount_amount:.2f}</span>
            </div>"""
    
    html_content += f"""
            <div class="total-line" style="font-size: 16px; border-top: 1px solid #000; padding-top: 5px;">
                <span>TOTAL:</span>
                <span>{currency_symbol}{sale.total_amount:.2f}</span>
            </div>
            <div class="total-line">
                <span>Payment:</span>
                <span>{sale.payment_method}</span>
            </div>
        </div>
        
        <div class="footer">
            <div>Thank you for your business!</div>
            <div>Powered by Cloud POS</div>
        </div>
        
        <script>
            // Auto-print when page loads (optional)
            // window.onload = function() {{ window.print(); }}
        </script>
    </body>
    </html>"""
    
    return html_content

# Returns functionality for cashiers and admins
@pos_bp.route('/returns')
@login_required
def returns_interface():
    """Returns interface for cashiers and admins"""
    # Check if user has permission to process returns
    if not (current_user.role in ['Admin', 'Manager', 'Cashier']):
        flash('You do not have permission to process returns.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if user has an open cash register (for cash refunds)
    register = CashRegister.query.filter_by(
        user_id=current_user.id,
        is_open=True
    ).first()
    
    if not register:
        flash('You must have an open cash register to process returns.', 'warning')
        return redirect(url_for('pos.open_register'))
    
    return render_template('pos/returns.html', register=register)

@pos_bp.route('/api/lookup-receipt', methods=['POST'])
@login_required
def lookup_receipt():
    """Lookup sale by receipt number"""
    data = request.get_json()
    receipt_number = data.get('receipt_number', '').strip()
    
    if not receipt_number:
        return jsonify({'error': 'Receipt number is required'}), 400
    
    # Find the sale
    sale = Sale.query.filter_by(receipt_number=receipt_number).first()
    if not sale:
        return jsonify({'error': f'Receipt {receipt_number} not found'}), 404
    
    # Check if sale has any existing returns
    existing_returns = SaleReturn.query.filter_by(original_sale_id=sale.id).all()
    
    # Calculate returned quantities for each item
    returned_quantities = {}
    for sale_return in existing_returns:
        if sale_return.status == 'Processed':
            for return_item in sale_return.items:
                original_item_id = return_item.original_sale_item_id
                if original_item_id not in returned_quantities:
                    returned_quantities[original_item_id] = 0
                returned_quantities[original_item_id] += return_item.quantity_returned
    
    # Build response data
    sale_data = {
        'id': sale.id,
        'receipt_number': sale.receipt_number,
        'created_at': sale.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'total_amount': float(sale.total_amount),
        'payment_method': sale.payment_method,
        'customer_name': sale.customer.name if sale.customer else 'Walk-in Customer',
        'cashier': sale.user.full_name,
        'currency': sale.currency,
        'items': []
    }
    
    for item in sale.sale_items:
        returned_qty = returned_quantities.get(item.id, 0)
        available_qty = item.quantity - returned_qty
        
        sale_data['items'].append({
            'id': item.id,
            'product_id': item.product_id,
            'product_name': item.product.name,
            'quantity_sold': item.quantity,
            'quantity_returned': returned_qty,
            'quantity_available': available_qty,
            'unit_price': float(item.unit_price),
            'total_price': float(item.total_price),
            'can_return': available_qty > 0
        })
    
    return jsonify({'success': True, 'sale': sale_data})

@pos_bp.route('/api/process-return', methods=['POST'])
@login_required  
def process_return():
    """Process a return and generate refund receipt"""
    try:
        data = request.get_json()
        sale_id = data.get('sale_id')
        return_items = data.get('items', [])
        return_reason = data.get('reason', '').strip()
        notes = data.get('notes', '').strip()
        
        if not sale_id or not return_items:
            return jsonify({'error': 'Sale ID and return items are required'}), 400
        
        if not return_reason:
            return jsonify({'error': 'Return reason is required'}), 400
        
        # Find the original sale
        original_sale = Sale.query.get(sale_id)
        if not original_sale:
            return jsonify({'error': 'Original sale not found'}), 404
        
        # Check if user has an open cash register
        register = CashRegister.query.filter_by(
            user_id=current_user.id,
            is_open=True
        ).first()
        
        if not register:
            return jsonify({'error': 'No open cash register found'}), 400
        
        # Calculate total return amount and validate items
        total_return_amount = 0
        valid_items = []
        
        for item_data in return_items:
            item_id = item_data.get('id')
            quantity_to_return = int(item_data.get('quantity', 0))
            
            if quantity_to_return <= 0:
                continue
                
            # Find the original sale item
            original_item = SaleItem.query.filter_by(
                id=item_id,
                sale_id=sale_id
            ).first()
            
            if not original_item:
                return jsonify({'error': f'Sale item {item_id} not found'}), 404
            
            # Check available quantity to return
            existing_returns = db.session.query(db.func.sum(SaleReturnItem.quantity_returned)).filter_by(
                original_sale_item_id=item_id
            ).join(SaleReturn).filter(
                SaleReturn.status == 'Processed'
            ).scalar() or 0
            
            available_qty = original_item.quantity - existing_returns
            
            if quantity_to_return > available_qty:
                return jsonify({'error': f'Cannot return {quantity_to_return} of {original_item.product.name}. Only {available_qty} available.'}), 400
            
            # Calculate return amount for this item
            item_return_amount = (original_item.unit_price * quantity_to_return)
            total_return_amount += item_return_amount
            
            valid_items.append({
                'original_item': original_item,
                'quantity': quantity_to_return,
                'amount': item_return_amount
            })
        
        if not valid_items:
            return jsonify({'error': 'No valid items to return'}), 400
        
        # Create the return record
        sale_return = SaleReturn()
        sale_return.return_number = generate_return_number()
        sale_return.original_sale_id = original_sale.id
        sale_return.user_id = current_user.id
        sale_return.return_amount = total_return_amount
        sale_return.return_reason = return_reason
        sale_return.notes = notes
        sale_return.status = 'Processed'  # Auto-approve for cashier/admin returns
        sale_return.created_at = datetime.utcnow()
        sale_return.processed_at = datetime.utcnow()
        
        db.session.add(sale_return)
        db.session.flush()  # Get the ID
        
        # Create return items and restore inventory
        for item_info in valid_items:
            original_item = item_info['original_item']
            quantity = item_info['quantity']
            amount = item_info['amount']
            
            # Create return item record
            return_item = SaleReturnItem()
            return_item.return_id = sale_return.id
            return_item.product_id = original_item.product_id
            return_item.original_sale_item_id = original_item.id
            return_item.quantity_returned = quantity
            return_item.unit_price = original_item.unit_price
            return_item.total_amount = amount
            
            db.session.add(return_item)
            
            # Restore inventory
            product = original_item.product
            product.stock_quantity += quantity
        
        # Deduct from cash register (for cash refunds)
        if original_sale.payment_method == 'Cash':
            register.cash_out += total_return_amount
            register.total_sales -= total_return_amount
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Return processed successfully. Refund amount: {get_currency_symbol()}{total_return_amount:.2f}',
            'return_number': sale_return.return_number,
            'return_amount': float(total_return_amount),
            'items_returned': len(valid_items)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process return: {str(e)}'}), 500

@pos_bp.route('/return/<return_number>/print')
@login_required
def print_return_receipt(return_number):
    """Generate HTML refund receipt for printing"""
    sale_return = SaleReturn.query.filter_by(return_number=return_number).first()
    if not sale_return:
        return jsonify({'error': 'Return record not found'}), 404
    
    currency_symbol = get_currency_symbol()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Refund Receipt {return_number}</title>
        <style>
            @media print {{
                body {{ margin: 0; padding: 20px; font-family: monospace; }}
                .no-print {{ display: none; }}
            }}
            body {{ 
                font-family: monospace; 
                width: 350px; 
                margin: 0 auto; 
                padding: 20px;
                background: white;
                color: black;
            }}
            .header {{ 
                text-align: center; 
                border-bottom: 2px dashed #000; 
                padding-bottom: 15px; 
                margin-bottom: 15px;
            }}
            .header h2 {{ margin: 0 0 10px 0; font-size: 18px; }}
            .refund-header {{ 
                text-align: center; 
                font-size: 16px; 
                font-weight: bold; 
                background: #000; 
                color: white; 
                padding: 10px; 
                margin: 15px 0; 
            }}
            .item {{ 
                display: flex; 
                justify-content: space-between; 
                margin: 8px 0; 
                padding: 2px 0;
            }}
            .item-name {{ flex: 1; }}
            .item-qty {{ width: 60px; text-align: center; }}
            .item-price {{ width: 80px; text-align: right; }}
            .total-section {{ 
                border-top: 2px dashed #000; 
                padding-top: 15px; 
                margin-top: 15px;
            }}
            .total-line {{ 
                display: flex; 
                justify-content: space-between; 
                margin: 5px 0;
                font-weight: bold;
            }}
            .footer {{ 
                text-align: center; 
                margin-top: 20px; 
                font-size: 12px; 
                border-top: 1px dashed #000;
                padding-top: 15px;
            }}
            .print-btn {{
                background: #dc3545;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                margin: 10px 5px;
            }}
            .print-controls {{
                text-align: center;
                margin: 20px 0;
            }}
            .detail-line {{ 
                display: flex; 
                justify-content: space-between; 
                margin: 3px 0; 
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="print-controls no-print">
            <button class="print-btn" onclick="window.print()">🖨️ Print Refund Receipt</button>
            <button class="print-btn" onclick="window.close()">❌ Close</button>
        </div>
        
        <div class="refund-header">*** REFUND RECEIPT ***</div>
        
        <div class="header">
            <h2>Cloud POS & Inventory Manager</h2>
            <div>Return #: {return_number}</div>
            <div>Original Receipt: {sale_return.original_sale.receipt_number}</div>
            <div>Date: {sale_return.created_at.strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div>Processed By: {sale_return.processed_by.full_name}</div>
            <div>Customer: {sale_return.original_sale.customer.name if sale_return.original_sale.customer else 'Walk-in'}</div>
        </div>
        
        <div class="detail-line">
            <span>Reason:</span>
            <span>{sale_return.return_reason}</span>
        </div>
        
        <div class="items">
            <div class="item" style="font-weight: bold; border-bottom: 1px solid #000;">
                <div class="item-name">Returned Item</div>
                <div class="item-qty">Qty</div>
                <div class="item-price">Refund</div>
            </div>"""
    
    for item in sale_return.items:
        html_content += f"""
            <div class="item">
                <div class="item-name">{item.product.name}</div>
                <div class="item-qty">{item.quantity_returned}</div>
                <div class="item-price">{currency_symbol}{item.total_amount:.2f}</div>
            </div>"""
    
    html_content += f"""
        </div>
        
        <div class="total-section">
            <div class="total-line">
                <span>TOTAL REFUND:</span>
                <span>{currency_symbol}{sale_return.return_amount:.2f}</span>
            </div>
            <div class="total-line">
                <span>Refund Method:</span>
                <span>{sale_return.original_sale.payment_method}</span>
            </div>
        </div>
        
        <div class="footer">
            <div>Items returned to inventory</div>
            <div>Thank you for your business!</div>
            <div style="margin-top: 10px; font-size: 10px;">
                Processed: {sale_return.processed_at.strftime('%Y-%m-%d %H:%M:%S') if sale_return.processed_at else 'N/A'}
            </div>
        </div>
        
        <script>
            window.onload = function() {{
                setTimeout(function() {{
                    window.print();
                }}, 500);
            }};
        </script>
    </body>
    </html>"""
    
    return html_content