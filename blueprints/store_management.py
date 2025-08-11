from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import Store, User, Product, StoreStock
from app import db
from utils import admin_required

store_management_bp = Blueprint('store_management', __name__)

@store_management_bp.route('/assign_products/<int:store_id>')
@login_required
@admin_required
def assign_products(store_id):
    """Show and manage product assignments for a store"""
    store = Store.query.get_or_404(store_id)
    
    # Get all products
    all_products = Product.query.filter_by(is_active=True).all()
    
    # Get products already assigned to this store
    assigned_products = db.session.query(Product, StoreStock.quantity).join(
        StoreStock, Product.id == StoreStock.product_id
    ).filter(StoreStock.store_id == store_id).all()
    
    # Get products not assigned to this store
    assigned_product_ids = [p.id for p, q in assigned_products]
    unassigned_products = [p for p in all_products if p.id not in assigned_product_ids]
    
    return render_template('admin/store_products.html', 
                         store=store, 
                         assigned_products=assigned_products,
                         unassigned_products=unassigned_products)

@store_management_bp.route('/api/assign_product', methods=['POST'])
@login_required
@admin_required
def assign_product_to_store():
    """API endpoint to assign a product to a store with quantity"""
    data = request.get_json()
    store_id = data.get('store_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 0)
    
    if not store_id or not product_id:
        return jsonify({'success': False, 'message': 'Store ID and Product ID are required'})
    
    try:
        # Check if assignment already exists
        existing = StoreStock.query.filter_by(store_id=store_id, product_id=product_id).first()
        if existing:
            return jsonify({'success': False, 'message': 'Product is already assigned to this store'})
        
        # Create new assignment
        store_stock = StoreStock()
        store_stock.store_id = store_id
        store_stock.product_id = product_id
        store_stock.quantity = quantity
        
        db.session.add(store_stock)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Product assigned successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@store_management_bp.route('/api/update_product_stock', methods=['POST'])
@login_required
@admin_required
def update_product_stock():
    """API endpoint to update product stock quantity in a store"""
    data = request.get_json()
    store_id = data.get('store_id')
    product_id = data.get('product_id')
    quantity = data.get('quantity', 0)
    
    if not store_id or not product_id:
        return jsonify({'success': False, 'message': 'Store ID and Product ID are required'})
    
    try:
        store_stock = StoreStock.query.filter_by(store_id=store_id, product_id=product_id).first()
        if not store_stock:
            return jsonify({'success': False, 'message': 'Product not assigned to this store'})
        
        store_stock.quantity = quantity
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Stock updated successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@store_management_bp.route('/api/remove_product_from_store', methods=['POST'])
@login_required
@admin_required
def remove_product_from_store():
    """API endpoint to remove a product from a store"""
    data = request.get_json()
    store_id = data.get('store_id')
    product_id = data.get('product_id')
    
    if not store_id or not product_id:
        return jsonify({'success': False, 'message': 'Store ID and Product ID are required'})
    
    try:
        store_stock = StoreStock.query.filter_by(store_id=store_id, product_id=product_id).first()
        if not store_stock:
            return jsonify({'success': False, 'message': 'Product not assigned to this store'})
        
        db.session.delete(store_stock)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Product removed from store'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@store_management_bp.route('/cashier_assignments')
@login_required
@admin_required
def cashier_assignments():
    """Show all cashier store assignments"""
    cashiers = User.query.filter(User.role.in_(['Cashier', 'Manager'])).all()
    stores = Store.query.filter_by(is_active=True).all()
    
    # Get summary data
    assignment_data = []
    for cashier in cashiers:
        store_name = cashier.default_store.name if cashier.store_id and cashier.default_store else 'No Store Assigned'
        product_count = 0
        if cashier.store_id:
            product_count = StoreStock.query.filter_by(store_id=cashier.store_id).count()
        
        assignment_data.append({
            'cashier': cashier,
            'store_name': store_name,
            'product_count': product_count
        })
    
    return render_template('admin/cashier_assignments.html', 
                         assignment_data=assignment_data, 
                         stores=stores)

@store_management_bp.route('/api/assign_cashier_to_store', methods=['POST'])
@login_required
@admin_required
def assign_cashier_to_store():
    """API endpoint to assign a cashier to a store"""
    data = request.get_json()
    user_id = data.get('user_id')
    store_id = data.get('store_id')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'User ID is required'})
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Update user's store assignment
        user.store_id = store_id if store_id != 0 else None
        db.session.commit()
        
        store_name = 'No Store' if not store_id or store_id == 0 else Store.query.get(store_id).name
        return jsonify({'success': True, 'message': f'Cashier assigned to {store_name} successfully'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})