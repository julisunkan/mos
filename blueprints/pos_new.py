from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from models import Product, Customer, Sale, SaleItem, CashRegister, UserStore
from app import db
from utils import generate_receipt_number, calculate_tax
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
        register = CashRegister(
            user_id=current_user.id,
            store_id=user_store.store_id,
            opening_balance=opening_balance,
            closing_balance=0,
            total_sales=0,
            cash_in=0,
            cash_out=0,
            is_open=True,
            opened_at=datetime.utcnow()
        )
        
        try:
            db.session.add(register)
            db.session.commit()
            flash(f'Cash register opened with ${opening_balance:.2f}', 'success')
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
        flash(f'Cash register closed. Closing balance: ${register.closing_balance:.2f}', 'success')
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
        
        # Create the sale
        sale = Sale(
            receipt_number=generate_receipt_number(),
            user_id=current_user.id,
            store_id=register.store_id,
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

@pos_bp.route('/receipt/<receipt_number>')
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
        for item in sale.items:
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