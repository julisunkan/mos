from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from models import Sale, SaleItem, Product, SaleReturn, SaleReturnItem, Customer

returns_bp = Blueprint('returns', __name__)

@returns_bp.route('/')
@login_required
def index():
    """Returns page for processing refunds"""
    return render_template('returns/index.html')

@returns_bp.route('/api/search_receipt')
@login_required
def search_receipt():
    """API endpoint to search for a sale by receipt number"""
    receipt_number = request.args.get('receipt_number', '').strip()
    
    if not receipt_number:
        return jsonify({'error': 'Receipt number is required'}), 400
    
    # Find the sale
    sale = Sale.query.filter_by(receipt_number=receipt_number).first()
    
    if not sale:
        return jsonify({'error': 'Receipt not found'}), 404
    
    # Check if user can access this sale (admin can access all, others only from their store)
    if current_user.role != 'admin':
        # For non-admin users, they can only process returns for sales from their assigned stores
        user_stores = [us.store_id for us in current_user.store_assignments]
        if sale.store_id not in user_stores:
            return jsonify({'error': 'Access denied to this receipt'}), 403
    
    # Check if sale is recent enough for returns (within 30 days)
    days_since_sale = (datetime.utcnow() - sale.created_at).days
    if days_since_sale > 30:
        return jsonify({'error': f'Sale is too old for returns ({days_since_sale} days ago). Returns allowed within 30 days only.'}), 400
    
    # Get existing returns for this sale
    existing_returns = SaleReturn.query.filter_by(original_sale_id=sale.id).all()
    returned_items = {}
    for ret in existing_returns:
        for item in ret.return_items:
            if item.product_id not in returned_items:
                returned_items[item.product_id] = 0
            returned_items[item.product_id] += item.quantity
    
    # Build response with sale items and return info
    items = []
    for item in sale.sale_items:
        returned_qty = returned_items.get(item.product_id, 0)
        available_qty = item.quantity - returned_qty
        
        items.append({
            'id': item.id,
            'product_id': item.product_id,
            'product_name': item.product.name,
            'quantity': item.quantity,
            'returned_quantity': returned_qty,
            'available_quantity': available_qty,
            'unit_price': float(item.unit_price),
            'total_price': float(item.total_price)
        })
    
    return jsonify({
        'sale': {
            'id': sale.id,
            'receipt_number': sale.receipt_number,
            'created_at': sale.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'customer_name': sale.customer.name if sale.customer else 'Walk-in Customer',
            'total_amount': float(sale.total_amount),
            'payment_method': sale.payment_method,
            'cashier': sale.user.full_name,
            'store_name': sale.store.name
        },
        'items': items,
        'days_since_sale': days_since_sale
    })

@returns_bp.route('/api/process_return', methods=['POST'])
@login_required
def process_return():
    """Process a return/refund"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('original_sale_id'):
            return jsonify({'error': 'Original sale ID is required'}), 400
        
        if not data.get('items') or len(data['items']) == 0:
            return jsonify({'error': 'No items selected for return'}), 400
        
        reason = data.get('reason', 'No reason provided')
        refund_method = data.get('refund_method', 'original_payment')
        
        # Get the original sale
        original_sale = Sale.query.get(data['original_sale_id'])
        if not original_sale:
            return jsonify({'error': 'Original sale not found'}), 404
        
        # Check permissions - same store access logic as search
        if current_user.role != 'admin':
            user_stores = [us.store_id for us in current_user.store_assignments]
            if original_sale.store_id not in user_stores:
                return jsonify({'error': 'Access denied'}), 403
        
        # Calculate return totals
        return_subtotal = 0
        return_tax = 0
        
        # Create the return record
        return_record = SaleReturn()
        return_record.return_number = f"RET-{datetime.utcnow().strftime('%Y%m%d')}-{original_sale.id}"
        return_record.original_sale_id = original_sale.id
        return_record.user_id = current_user.id
        # Note: customer_id and store_id not in current schema
        return_record.return_reason = reason
        return_record.notes = f"Refund method: {refund_method}"
        return_record.status = 'Completed'
        return_record.return_amount = 0  # Will be calculated
        return_record.processed_at = datetime.utcnow()
        
        db.session.add(return_record)
        db.session.flush()  # Get the return ID
        
        # Process each return item
        for item_data in data['items']:
            if item_data.get('return_quantity', 0) <= 0:
                continue
            
            # Get the original sale item
            sale_item = SaleItem.query.get(item_data['sale_item_id'])
            if not sale_item or sale_item.sale_id != original_sale.id:
                db.session.rollback()
                return jsonify({'error': f'Invalid sale item ID: {item_data["sale_item_id"]}'}), 400
            
            return_quantity = int(item_data['return_quantity'])
            
            # Check if return quantity is valid
            if return_quantity > sale_item.quantity:
                db.session.rollback()
                return jsonify({'error': f'Cannot return more than purchased for {sale_item.product.name}'}), 400
            
            # Calculate proportional refund amount
            proportion = return_quantity / sale_item.quantity
            refund_amount = float(sale_item.total_price) * proportion
            
            # Create return item
            return_item = SaleReturnItem()
            return_item.return_id = return_record.id
            return_item.original_sale_item_id = sale_item.id
            return_item.product_id = sale_item.product_id
            return_item.quantity = return_quantity
            return_item.unit_price = sale_item.unit_price
            return_item.total_refund = refund_amount
            
            db.session.add(return_item)
            
            # Update product stock (return to inventory)
            product = Product.query.get(sale_item.product_id)
            if product:
                product.stock_quantity += return_quantity
            
            # Add to return totals
            return_subtotal += refund_amount
        
        # Update return record totals
        return_record.return_amount = return_subtotal
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'return_id': return_record.id,
            'return_number': return_record.return_number,
            'refund_amount': float(return_record.return_amount)
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing return: {str(e)}")
        return jsonify({'error': 'Failed to process return'}), 500

@returns_bp.route('/history')
@login_required
def history():
    """View returns history"""
    page = request.args.get('page', 1, type=int)
    
    # Get returns for current user or all if admin
    if current_user.role == 'admin':
        returns = SaleReturn.query.order_by(SaleReturn.processed_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
    else:
        returns = SaleReturn.query.filter_by(user_id=current_user.id).order_by(
            SaleReturn.processed_at.desc()
        ).paginate(page=page, per_page=20, error_out=False)
    
    return render_template('returns/history.html', returns=returns)

@returns_bp.route('/receipt/<int:return_id>')
@login_required
def return_receipt(return_id):
    """View return receipt"""
    return_record = SaleReturn.query.get_or_404(return_id)
    
    # Check if user can view this return
    if current_user.role != 'admin' and return_record.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('returns.index'))
    
    return render_template('returns/receipt.html', return_record=return_record)