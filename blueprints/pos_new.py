from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from models import Product, Customer, Sale, SaleItem, CashRegister, UserStore
from app import db
from utils import generate_receipt_number, get_default_currency, format_currency, calculate_tax
from datetime import datetime
import io

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
            product = Product.query.get(item_data['product_id'])
            if not product:
                return jsonify({'error': f'Product not found: {item_data["product_id"]}'}), 400
            
            quantity = int(item_data['quantity'])
            if product.stock_quantity < quantity:
                return jsonify({'error': f'Insufficient stock for {product.name}'}), 400
            
            unit_price = float(item_data.get('unit_price', product.selling_price))
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
            tax_total += calculate_tax(total_price, product.tax_rate or 0)
        
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
        
        # Find the sale by receipt number
        sale = Sale.query.filter_by(receipt_number=receipt_number).first()
        if not sale:
            return jsonify({'error': 'Receipt not found'}), 404
        
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
            p.drawString(450, y_pos, f"${item.total_price:.2f}")
            y_pos -= 15
        
        # Totals
        y_pos -= 20
        p.line(50, y_pos, width-50, y_pos)
        y_pos -= 20
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(350, y_pos, f"Total: ${sale.total_amount:.2f}")
        
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
    # Find the sale by receipt number
    sale = Sale.query.filter_by(receipt_number=receipt_number).first()
    if not sale:
        return jsonify({'error': 'Receipt not found'}), 404
    
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
                <div class="item-price">${item.total_price:.2f}</div>
            </div>"""
    
    html_content += f"""
        </div>
        
        <div class="total-section">
            <div class="total-line">
                <span>Subtotal:</span>
                <span>${sale.subtotal:.2f}</span>
            </div>
            <div class="total-line">
                <span>Tax:</span>
                <span>${sale.tax_amount:.2f}</span>
            </div>"""
    
    if sale.discount_amount > 0:
        html_content += f"""
            <div class="total-line">
                <span>Discount:</span>
                <span>-${sale.discount_amount:.2f}</span>
            </div>"""
    
    html_content += f"""
            <div class="total-line" style="font-size: 16px; border-top: 1px solid #000; padding-top: 5px;">
                <span>TOTAL:</span>
                <span>${sale.total_amount:.2f}</span>
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