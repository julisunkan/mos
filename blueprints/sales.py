from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, send_file, current_app
from flask_login import login_required, current_user
from sqlalchemy import text, or_
from datetime import datetime
import uuid
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from app import db
from models import Product, Sale, SaleItem, Customer, Store

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/new_sale')
@login_required
def new_sale():
    """Display the new sale page"""
    # Get products for the current user's store
    if current_user.role == 'admin':
        products = Product.query.filter_by(is_active=True).all()
    else:
        # Get products for user's assigned stores
        store_ids = [store.id for store in current_user.store_assignments]
        if store_ids:
            # For now, show all products - store filtering can be added later
            products = Product.query.filter_by(is_active=True).all()
        else:
            products = []
    
    customers = Customer.query.filter_by(is_active=True).all()
    
    return render_template('sales/new_sale.html', 
                         products=products, 
                         customers=customers)

@sales_bp.route('/api/products/search')
@login_required
def search_products():
    """API endpoint for product search"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify([])
    
    # Base query for active products
    base_query = Product.query.filter(Product.is_active == True)
    
    # Filter by user's stores if not admin
    if current_user.role != 'admin':
        store_ids = [store.id for store in current_user.store_assignments]
        if not store_ids:
            return jsonify([])
    
    # Search by name, SKU, or barcode
    products = base_query.filter(
        or_(
            Product.name.ilike(f'%{query}%'),
            Product.sku.ilike(f'%{query}%'),
            Product.barcode.ilike(f'%{query}%')
        )
    ).limit(20).all()
    
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'barcode': p.barcode,
        'price': float(p.selling_price),
        'stock': p.stock_quantity,
        'tax_rate': float(p.tax_rate) if p.tax_rate else 0.0
    } for p in products])

@sales_bp.route('/api/process_sale', methods=['POST'])
@login_required
def process_sale():
    """Process a new sale"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('items') or len(data['items']) == 0:
            return jsonify({'error': 'No items in cart'}), 400
        
        payment_method = data.get('payment_method', 'cash')
        customer_id = data.get('customer_id')
        
        # Get user's primary store
        user_store = current_user.store_assignments[0] if current_user.store_assignments else None
        if not user_store:
            return jsonify({'error': 'No store assigned to user'}), 400
        
        # Calculate totals
        subtotal = 0
        tax_amount = 0
        
        # Create the sale
        sale = Sale()
        sale.receipt_number = f"REC-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        sale.user_id = current_user.id
        sale.customer_id = customer_id if customer_id else None
        sale.store_id = user_store.id
        sale.payment_method = payment_method
        sale.subtotal = 0  # Will be calculated
        sale.tax_amount = 0  # Will be calculated  
        sale.total_amount = 0  # Will be calculated
        sale.created_at = datetime.utcnow()
        
        db.session.add(sale)
        db.session.flush()  # Get the sale ID
        
        # Process each item
        for item_data in data['items']:
            product = Product.query.get(item_data['product_id'])
            if not product:
                db.session.rollback()
                return jsonify({'error': f'Product not found: {item_data["product_id"]}'}), 400
            
            quantity = int(item_data['quantity'])
            unit_price = float(item_data['unit_price'])
            
            # Check stock
            if product.stock_quantity < quantity:
                db.session.rollback()
                return jsonify({'error': f'Insufficient stock for {product.name}'}), 400
            
            # Calculate item totals
            item_subtotal = quantity * unit_price
            item_tax = item_subtotal * (float(product.tax_rate) / 100 if product.tax_rate else 0)
            item_total = item_subtotal
            
            # Create sale item
            sale_item = SaleItem()
            sale_item.sale_id = sale.id
            sale_item.product_id = product.id
            sale_item.quantity = quantity
            sale_item.unit_price = unit_price
            sale_item.total_price = item_total
            db.session.add(sale_item)
            
            # Update product stock
            product.stock_quantity -= quantity
            
            # Add to sale totals
            subtotal += item_subtotal
            tax_amount += item_tax
        
        # Update sale totals
        total_amount = subtotal + tax_amount
        sale.subtotal = subtotal
        sale.tax_amount = tax_amount
        sale.total_amount = total_amount
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'sale_id': sale.id,
            'receipt_number': sale.receipt_number,
            'total_amount': total_amount
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing sale: {str(e)}")
        return jsonify({'error': 'Failed to process sale'}), 500

@sales_bp.route('/receipt/<int:sale_id>')
@login_required
def view_receipt(sale_id):
    """View receipt in browser"""
    sale = Sale.query.get_or_404(sale_id)
    
    # Check if user can view this receipt
    if current_user.role != 'admin' and sale.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('sales.new_sale'))
    
    return render_template('sales/receipt.html', sale=sale)

@sales_bp.route('/receipt/<int:sale_id>/pdf')
@login_required
def download_receipt_pdf(sale_id):
    """Generate and download PDF receipt"""
    sale = Sale.query.get_or_404(sale_id)
    
    # Check if user can download this receipt
    if current_user.role != 'admin' and sale.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('sales.new_sale'))
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=1  # Center
    )
    
    normal_style = styles['Normal']
    
    # Build PDF content
    content = []
    
    # Store header
    content.append(Paragraph(f"<b>{sale.store.name}</b>", title_style))
    if sale.store.address:
        content.append(Paragraph(sale.store.address, normal_style))
    if sale.store.phone:
        content.append(Paragraph(f"Phone: {sale.store.phone}", normal_style))
    
    content.append(Spacer(1, 20))
    
    # Receipt details
    content.append(Paragraph(f"<b>Receipt #{sale.receipt_number}</b>", normal_style))
    content.append(Paragraph(f"Date: {sale.created_at.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    content.append(Paragraph(f"Cashier: {sale.user.full_name}", normal_style))
    if sale.customer:
        content.append(Paragraph(f"Customer: {sale.customer.name}", normal_style))
    
    content.append(Spacer(1, 20))
    
    # Items table
    table_data = [['Item', 'Qty', 'Price', 'Total']]
    for item in sale.sale_items:
        table_data.append([
            item.product.name,
            str(item.quantity),
            f"${item.unit_price:.2f}",
            f"${item.total_price:.2f}"
        ])
    
    # Add totals
    table_data.append(['', '', 'Subtotal:', f"${sale.subtotal:.2f}"])
    table_data.append(['', '', 'Tax:', f"${sale.tax_amount:.2f}"])
    table_data.append(['', '', 'TOTAL:', f"${sale.total_amount:.2f}"])
    
    table = Table(table_data, colWidths=[3*inch, 0.8*inch, 1*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -4), colors.beige),
        ('FONTNAME', (0, -3), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 14),
        ('GRID', (0, 0), (-1, -4), 1, colors.black),
        ('BOX', (0, -3), (-1, -1), 2, colors.black),
    ]))
    
    content.append(table)
    content.append(Spacer(1, 20))
    
    # Footer
    content.append(Paragraph(f"Payment Method: {sale.payment_method.title()}", normal_style))
    content.append(Paragraph("Thank you for your business!", normal_style))
    
    # Build PDF
    doc.build(content)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"receipt_{sale.receipt_number}.pdf",
        mimetype='application/pdf'
    )

@sales_bp.route('/sales_history')
@login_required
def sales_history():
    """View sales history"""
    page = request.args.get('page', 1, type=int)
    
    # Get sales for current user or all if admin
    if current_user.role == 'admin':
        sales = Sale.query.order_by(Sale.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
    else:
        sales = Sale.query.filter_by(user_id=current_user.id).order_by(
            Sale.created_at.desc()
        ).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('sales/history.html', sales=sales)