from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from forms import StoreForm, StockTransferForm, PurchaseOrderForm, SupplierForm
from models import Store, UserStore, StoreStock, Product, StockTransfer, StockTransferItem, PurchaseOrder, PurchaseOrderItem, Supplier, User, Sale, PromotionCode, CashRegister, SaleReturn
from app import db
from utils import admin_required, generate_transfer_number, generate_po_number
from datetime import datetime
from blueprints.store_assignment_helper import ensure_store_has_products, fix_store_setup

stores_bp = Blueprint('stores', __name__)

@stores_bp.route('/')
@login_required
@admin_required
def index():
    stores = Store.query.filter_by(is_active=True).all()
    return render_template('stores/index.html', stores=stores)

@stores_bp.route('/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_store():
    form = StoreForm()
    
    # Populate manager choices
    managers = User.query.filter_by(is_active=True).all()
    form.manager_id.choices = [(0, '--- No Manager ---')] + [(u.id, f"{u.username} ({u.first_name} {u.last_name})") for u in managers]
    
    if form.validate_on_submit():
        # Handle manager_id (0 means no manager)
        manager_id = form.manager_id.data if form.manager_id.data != 0 else None
        
        store = Store()
        store.name = form.name.data
        store.address = form.address.data
        store.phone = form.phone.data
        store.email = form.email.data
        store.manager_id = manager_id
        
        try:
            db.session.add(store)
            db.session.flush()  # Get the store ID
            
            # Auto-assign store to its manager if specified
            if manager_id:
                manager = User.query.get(manager_id)
                if manager:
                    # Always assign the manager to the store, even if they have another store
                    manager.store_id = store.id
                    
                    # Also create UserStore relationship for consistency
                    user_store = UserStore()
                    user_store.user_id = manager_id
                    user_store.store_id = store.id
                    user_store.is_default = True
                    db.session.add(user_store)
                    
                    flash(f'Store {store.name} created and assigned to manager {manager.username}!', 'success')
                else:
                    flash(f'Store {store.name} created successfully!', 'success')
            else:
                # No manager specified, store created without assignment
                flash(f'Store {store.name} created successfully! Remember to assign a manager or cashiers.', 'info')
            
            # Auto-assign products to the new store using helper function
            success, message, products_assigned = ensure_store_has_products(store.id, min_products=5)
            if success and products_assigned > 0:
                flash(f'{message}. {products_assigned} products auto-assigned for immediate operation.', 'info')
            
            db.session.commit()
            return redirect(url_for('stores.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating store: {str(e)}', 'error')
    
    return render_template('stores/form.html', form=form, title='New Store')

@stores_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_store(id):
    store = Store.query.get_or_404(id)
    form = StoreForm(obj=store)
    
    # Populate manager choices
    managers = User.query.filter_by(is_active=True).all()
    form.manager_id.choices = [(0, '--- No Manager ---')] + [(u.id, f"{u.username} ({u.first_name} {u.last_name})") for u in managers]
    
    if form.validate_on_submit():
        # Handle manager_id (0 means no manager)
        manager_id = form.manager_id.data if form.manager_id.data != 0 else None
        
        store.name = form.name.data
        store.address = form.address.data
        store.phone = form.phone.data
        store.email = form.email.data
        store.manager_id = manager_id
        
        try:
            # Handle manager assignment changes
            old_manager_id = store.manager_id
            
            # If manager changed, update assignments
            if old_manager_id != manager_id:
                # Remove old manager assignment if they're only assigned to this store
                if old_manager_id:
                    old_manager = User.query.get(old_manager_id)
                    if old_manager and old_manager.store_id == store.id:
                        old_manager.store_id = None
                
                # Assign new manager if specified
                if manager_id:
                    new_manager = User.query.get(manager_id)
                    if new_manager:
                        # Always assign the manager to the store
                        new_manager.store_id = store.id
                        
                        # Create UserStore relationship if it doesn't exist
                        existing_relationship = UserStore.query.filter_by(
                            user_id=manager_id, 
                            store_id=store.id
                        ).first()
                        
                        if not existing_relationship:
                            user_store = UserStore()
                            user_store.user_id = manager_id
                            user_store.store_id = store.id
                            user_store.is_default = True
                            db.session.add(user_store)
                        
                        flash(f'Store {store.name} updated and assigned to manager {new_manager.username}!', 'success')
                    else:
                        flash(f'Store {store.name} updated successfully!', 'success')
                else:
                    flash(f'Store {store.name} updated successfully!', 'success')
            else:
                flash(f'Store {store.name} updated successfully!', 'success')
            
            db.session.commit()
            return redirect(url_for('stores.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating store: {str(e)}', 'error')
    
    return render_template('stores/form.html', form=form, title='Edit Store', store=store)

@stores_bp.route('/<int:id>/stock')
@login_required
def store_stock(id):
    store = Store.query.get_or_404(id)
    stock_items = db.session.query(StoreStock, Product).join(Product).filter(StoreStock.store_id == id).all()
    return render_template('stores/stock.html', store=store, stock_items=stock_items)

@stores_bp.route('/suppliers')
@login_required
@admin_required
def suppliers():
    suppliers = Supplier.query.filter_by(is_active=True).all()
    return render_template('stores/suppliers.html', suppliers=suppliers)

@stores_bp.route('/suppliers/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_supplier():
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier()
        supplier.name = form.name.data
        supplier.contact_person = form.contact_person.data
        supplier.email = form.email.data
        supplier.phone = form.phone.data
        supplier.address = form.address.data
        
        try:
            db.session.add(supplier)
            db.session.commit()
            flash(f'Supplier {supplier.name} created successfully!', 'success')
            return redirect(url_for('stores.suppliers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating supplier: {str(e)}', 'error')
    
    return render_template('stores/supplier_form.html', form=form, title='New Supplier')

@stores_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_store(id):
    """Safely delete a store with comprehensive relationship cleanup"""
    store = Store.query.get_or_404(id)
    
    try:
        # Check for dependencies and provide detailed warnings
        warnings = []
        blocking_dependencies = []
        
        # Check for sales (these prevent deletion)
        sales_count = Sale.query.filter_by(store_id=id).count()
        if sales_count > 0:
            blocking_dependencies.append(f"{sales_count} sales transactions")
        
        # Check for purchase orders (these prevent deletion)  
        po_count = PurchaseOrder.query.filter_by(store_id=id).count()
        if po_count > 0:
            blocking_dependencies.append(f"{po_count} purchase orders")
        
        # Check for cash registers (these prevent deletion)
        cash_register_count = CashRegister.query.filter_by(store_id=id).count()
        if cash_register_count > 0:
            blocking_dependencies.append(f"{cash_register_count} cash register records")
        
        # Check for returns related to sales from this store (these prevent deletion)
        returns_count = db.session.query(SaleReturn).join(Sale, SaleReturn.original_sale_id == Sale.id).filter(Sale.store_id == id).count()
        if returns_count > 0:
            blocking_dependencies.append(f"{returns_count} return records")
        
        # If there are blocking dependencies, refuse deletion
        if blocking_dependencies:
            flash(f'Cannot delete store "{store.name}". It has critical business data: {", ".join(blocking_dependencies)}. '
                  'You must first transfer or remove these records to safely delete the store.', 'error')
            return redirect(url_for('stores.index'))
        
        # Check for non-blocking dependencies that will be cleaned up
        assigned_users = User.query.filter_by(store_id=id).count()
        if assigned_users > 0:
            warnings.append(f"{assigned_users} users will be unassigned from this store")
        
        user_store_assignments = UserStore.query.filter_by(store_id=id).count()
        if user_store_assignments > 0:
            warnings.append(f"{user_store_assignments} user-store relationship records will be removed")
        
        stock_items = StoreStock.query.filter_by(store_id=id).count()
        if stock_items > 0:
            warnings.append(f"{stock_items} inventory items will be removed from this store")
        
        promotion_codes = PromotionCode.query.filter_by(store_id=id).count()
        if promotion_codes > 0:
            warnings.append(f"{promotion_codes} store-specific promotion codes will be removed")
        
        # Proceed with safe deletion - clean up all relationships
        
        # 1. Unassign users from this store
        User.query.filter_by(store_id=id).update({User.store_id: None})
        
        # 2. Remove user-store assignments
        UserStore.query.filter_by(store_id=id).delete()
        
        # 3. Remove store stock items
        StoreStock.query.filter_by(store_id=id).delete()
        
        # 4. Remove store-specific promotion codes
        PromotionCode.query.filter_by(store_id=id).delete()
        
        # 5. Handle pending stock transfers involving this store
        # Set transfers to cancelled status rather than deleting them
        pending_transfers_from = StockTransfer.query.filter_by(from_store_id=id, status='Pending').all()
        for transfer in pending_transfers_from:
            transfer.status = 'Cancelled'
            transfer.notes = f"Cancelled due to source store deletion. {transfer.notes or ''}".strip()
        
        pending_transfers_to = StockTransfer.query.filter_by(to_store_id=id, status='Pending').all()
        for transfer in pending_transfers_to:
            transfer.status = 'Cancelled'  
            transfer.notes = f"Cancelled due to destination store deletion. {transfer.notes or ''}".strip()
        
        # 6. Finally delete the store itself
        db.session.delete(store)
        
        # Commit all changes
        db.session.commit()
        
        # Show success message with details of what was cleaned up
        success_message = f'Store "{store.name}" has been safely deleted.'
        if warnings:
            success_message += f' Cleaned up: {", ".join(warnings)}.'
        
        flash(success_message, 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting store: {str(e)}', 'error')
    
    return redirect(url_for('stores.index'))

@stores_bp.route('/<int:id>/deletion-info')
@login_required
@admin_required 
def store_deletion_info(id):
    """Show detailed information about what will be affected by store deletion"""
    store = Store.query.get_or_404(id)
    
    # Gather dependency information
    dependencies = {
        'blocking': [],
        'cleanup': []
    }
    
    # Blocking dependencies
    sales_count = Sale.query.filter_by(store_id=id).count()
    if sales_count > 0:
        dependencies['blocking'].append({
            'type': 'Sales Transactions', 
            'count': sales_count,
            'description': 'Historical sales data that cannot be deleted'
        })
    
    po_count = PurchaseOrder.query.filter_by(store_id=id).count()
    if po_count > 0:
        dependencies['blocking'].append({
            'type': 'Purchase Orders',
            'count': po_count, 
            'description': 'Supply chain records that must be preserved'
        })
    
    cash_register_count = CashRegister.query.filter_by(store_id=id).count() 
    if cash_register_count > 0:
        dependencies['blocking'].append({
            'type': 'Cash Register Records',
            'count': cash_register_count,
            'description': 'Financial audit trail records'
        })
    
    # Non-blocking dependencies that will be cleaned up
    assigned_users = User.query.filter_by(store_id=id).all()
    if assigned_users:
        dependencies['cleanup'].append({
            'type': 'User Assignments',
            'count': len(assigned_users),
            'description': f'Users: {", ".join([u.username for u in assigned_users])} will be unassigned'
        })
    
    user_store_assignments = UserStore.query.filter_by(store_id=id).count()
    if user_store_assignments > 0:
        dependencies['cleanup'].append({
            'type': 'User-Store Relationships',
            'count': user_store_assignments,
            'description': 'Internal assignment records will be removed'
        })
    
    stock_items = StoreStock.query.filter_by(store_id=id).count()
    if stock_items > 0:
        dependencies['cleanup'].append({
            'type': 'Inventory Items',
            'count': stock_items,
            'description': 'Store-specific product stock records will be removed'
        })
    
    promotion_codes = PromotionCode.query.filter_by(store_id=id).count()
    if promotion_codes > 0:
        dependencies['cleanup'].append({
            'type': 'Promotion Codes',
            'count': promotion_codes,
            'description': 'Store-specific promotional offers will be removed'
        })
    
    return render_template('stores/deletion_info.html', store=store, dependencies=dependencies)

@stores_bp.route('/purchase-orders')
@login_required
def purchase_orders():
    page = request.args.get('page', 1, type=int)
    purchase_orders = PurchaseOrder.query.order_by(PurchaseOrder.created_at.desc()).all()
    return render_template('stores/purchase_orders.html', purchase_orders=purchase_orders)

@stores_bp.route('/stock-transfers')
@login_required
def stock_transfers():
    page = request.args.get('page', 1, type=int)
    transfers = StockTransfer.query.order_by(StockTransfer.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('stores/stock_transfers.html', transfers=transfers)

@stores_bp.route('/stock-transfers/new', methods=['GET', 'POST'])
@login_required
def new_stock_transfer():
    form = StockTransferForm()
    
    # Populate form choices
    stores = Store.query.filter_by(is_active=True).all()
    products = Product.query.filter_by(is_active=True).all()
    form.from_store_id.choices = [(s.id, s.name) for s in stores]
    form.to_store_id.choices = [(s.id, s.name) for s in stores]
    form.product_id.choices = [(p.id, f"{p.name} ({p.sku})") for p in products]
    
    if form.validate_on_submit():
        transfer = StockTransfer()
        transfer.transfer_number = generate_transfer_number()
        transfer.from_store_id = form.from_store_id.data
        transfer.to_store_id = form.to_store_id.data
        transfer.user_id = current_user.id
        transfer.notes = form.notes.data
        
        try:
            db.session.add(transfer)
            db.session.commit()
            flash(f'Stock transfer {transfer.transfer_number} created successfully!', 'success')
            return redirect(url_for('stores.stock_transfers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating stock transfer: {str(e)}', 'error')
    
    return render_template('stores/transfer_form.html', form=form, title='New Stock Transfer')

@stores_bp.route('/purchase-orders/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_purchase_order():
    form = PurchaseOrderForm()
    
    # Populate form choices
    suppliers = Supplier.query.filter_by(is_active=True).all()
    stores = Store.query.filter_by(is_active=True).all()
    form.supplier_id.choices = [(s.id, s.name) for s in suppliers]
    form.store_id.choices = [(s.id, s.name) for s in stores]
    
    if form.validate_on_submit():
        po = PurchaseOrder()
        po.po_number = generate_po_number()
        po.supplier_id = form.supplier_id.data
        po.user_id = current_user.id
        po.expected_date = form.expected_date.data
        po.notes = form.notes.data
        po.status = 'Draft'
        
        try:
            db.session.add(po)
            db.session.commit()
            flash(f'Purchase order {po.po_number} created successfully!', 'success')
            return redirect(url_for('stores.purchase_orders'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating purchase order: {str(e)}', 'error')
    
    return render_template('stores/purchase_order_form.html', form=form, title='New Purchase Order')

@stores_bp.route('/purchase-orders/<int:id>')
@login_required
def view_purchase_order(id):
    po = PurchaseOrder.query.get_or_404(id)
    return render_template('stores/purchase_order_view.html', po=po)

@stores_bp.route('/stock-transfers/<int:id>')
@login_required  
def view_stock_transfer(id):
    transfer = StockTransfer.query.get_or_404(id)
    return render_template('stores/transfer_view.html', transfer=transfer)