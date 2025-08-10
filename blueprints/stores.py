from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from forms import StoreForm, StockTransferForm, PurchaseOrderForm, SupplierForm
from models import Store, UserStore, StoreStock, Product, StockTransfer, StockTransferItem, PurchaseOrder, PurchaseOrderItem, Supplier, User
from app import db
from utils import admin_required, generate_transfer_number, generate_po_number
from datetime import datetime

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
            db.session.commit()
            flash(f'Store {store.name} created successfully!', 'success')
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
            db.session.commit()
            flash(f'Store {store.name} updated successfully!', 'success')
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