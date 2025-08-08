from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from models import Sale, Product, Customer, User, SaleItem
from app import db
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from utils import format_currency, get_default_currency

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.has_permission('read_reports') and not current_user.has_permission('all'):
        flash('You do not have permission to view reports.', 'error')
        return redirect(url_for('dashboard'))
    
    # Date range for filtering (default: last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Sales statistics
    total_sales = Sale.query.filter(Sale.created_at.between(start_date, end_date)).count()
    total_revenue = db.session.query(func.sum(Sale.total_amount)).filter(
        Sale.created_at.between(start_date, end_date)
    ).scalar() or 0
    
    # Average sale amount
    avg_sale = total_revenue / total_sales if total_sales > 0 else 0
    
    # Top selling products
    top_products = db.session.query(
        Product.name,
        func.sum(SaleItem.quantity).label('total_sold'),
        func.sum(SaleItem.total_price).label('total_revenue')
    ).join(SaleItem).join(Sale).filter(
        Sale.created_at.between(start_date, end_date)
    ).group_by(Product.id, Product.name).order_by(
        desc('total_sold')
    ).limit(10).all()
    
    # Daily sales for chart
    daily_sales = db.session.query(
        func.date(Sale.created_at).label('date'),
        func.sum(Sale.total_amount).label('total'),
        func.count(Sale.id).label('count')
    ).filter(
        Sale.created_at.between(start_date, end_date)
    ).group_by(func.date(Sale.created_at)).order_by('date').all()
    
    # Low stock products
    low_stock_count = Product.query.filter(
        Product.is_active == True,
        Product.stock_quantity <= Product.low_stock_threshold
    ).count()
    
    return render_template('reports/dashboard.html',
                         total_sales=total_sales,
                         total_revenue=total_revenue,
                         avg_sale=avg_sale,
                         top_products=top_products,
                         daily_sales=daily_sales,
                         low_stock_count=low_stock_count,
                         start_date=start_date,
                         end_date=end_date)

@reports_bp.route('/sales')
@login_required
def sales():
    if not current_user.has_permission('read_reports') and not current_user.has_permission('all'):
        flash('You do not have permission to view reports.', 'error')
        return redirect(url_for('dashboard'))
    
    page = request.args.get('page', 1, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id', type=int)
    
    query = Sale.query
    
    # Apply date filters
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(Sale.created_at >= start_date)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        # Add 1 day to include the entire end date
        end_date = end_date + timedelta(days=1)
        query = query.filter(Sale.created_at < end_date)
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    sales = query.order_by(Sale.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get users for filter dropdown
    users = User.query.filter_by(is_active=True).all()
    
    # Calculate totals for filtered results
    total_amount = db.session.query(func.sum(Sale.total_amount)).filter(
        *[condition for condition in [
            Sale.created_at >= start_date if start_date else None,
            Sale.created_at < end_date if end_date else None,
            Sale.user_id == user_id if user_id else None
        ] if condition is not None]
    ).scalar() or 0
    
    return render_template('reports/sales.html',
                         sales=sales,
                         users=users,
                         total_amount=total_amount,
                         filters={
                             'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
                             'end_date': (end_date - timedelta(days=1)).strftime('%Y-%m-%d') if end_date else '',
                             'user_id': user_id
                         })

@reports_bp.route('/sale/<int:sale_id>/details')
@login_required
def sale_details(sale_id):
    """Get detailed information about a specific sale"""
    if not current_user.has_permission('read_reports') and not current_user.has_permission('all'):
        return jsonify({'error': 'Permission denied'}), 403
    
    sale = Sale.query.get_or_404(sale_id)
    
    # Build sale details JSON
    sale_data = {
        'id': sale.id,
        'receipt_number': sale.receipt_number,
        'created_at': sale.created_at.isoformat(),
        'user_name': sale.user.full_name,
        'customer_name': sale.customer.name if sale.customer else None,
        'payment_method': sale.payment_method,
        'subtotal': float(sale.subtotal),
        'tax_amount': float(sale.tax_amount),
        'discount_amount': float(sale.discount_amount),
        'total_amount': float(sale.total_amount),
        'notes': sale.notes,
        'payment_status': getattr(sale, 'payment_status', 'Paid'),
        'items': []
    }
    
    # Add sale items
    for item in sale.sale_items:
        sale_data['items'].append({
            'product_name': item.product.name,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price),
            'total_price': float(item.total_price)
        })
    
    return jsonify(sale_data)

@reports_bp.route('/sales/print')
@login_required
def sales_print():
    """Generate print-formatted sales report"""
    if not current_user.has_permission('read_reports') and not current_user.has_permission('all'):
        flash('You do not have permission to view reports.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id', type=int)
    
    query = Sale.query
    
    # Apply date filters
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        query = query.filter(Sale.created_at >= start_date)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        # Add 1 day to include the entire end date
        end_date = end_date + timedelta(days=1)
        query = query.filter(Sale.created_at < end_date)
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    # Get all sales for the report (no pagination for print)
    sales = query.order_by(Sale.created_at.desc()).all()
    
    # Get users for display
    users = User.query.filter_by(is_active=True).all()
    user_dict = {u.id: u.full_name for u in users}
    
    # Calculate totals
    total_amount = sum(sale.total_amount for sale in sales)
    total_transactions = len(sales)
    avg_sale = total_amount / total_transactions if total_transactions > 0 else 0
    
    return render_template('reports/sales_print.html',
                         sales=sales,
                         total_amount=total_amount,
                         total_transactions=total_transactions,
                         avg_sale=avg_sale,
                         current_time=datetime.now(),
                         filters={
                             'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
                             'end_date': (end_date - timedelta(days=1)).strftime('%Y-%m-%d') if end_date else '',
                             'user_id': user_id,
                             'user_name': user_dict.get(user_id, 'All Users') if user_id else 'All Users'
                         })
