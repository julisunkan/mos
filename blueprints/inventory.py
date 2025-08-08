from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from forms import ProductForm
from models import Product, Category
from app import db
from utils import generate_sku

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/products')
@login_required
def products():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category_id = request.args.get('category', type=int)
    
    query = Product.query
    
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.sku.ilike(f'%{search}%')
            )
        )
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    products = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    categories = Category.query.filter_by(is_active=True).all()
    
    return render_template('inventory/products.html', 
                         products=products, 
                         categories=categories,
                         search=search,
                         selected_category=category_id)

@inventory_bp.route('/products/new', methods=['GET', 'POST'])
@login_required
def new_product():
    if not current_user.has_permission('write_inventory') and not current_user.has_permission('all'):
        flash('You do not have permission to create products.', 'error')
        return redirect(url_for('inventory.products'))
    
    form = ProductForm()
    if form.validate_on_submit():
        product = Product(
            name=form.name.data,
            description=form.description.data,
            sku=form.sku.data,
            barcode=form.barcode.data,
            category_id=form.category_id.data,
            cost_price=form.cost_price.data,
            selling_price=form.selling_price.data,
            stock_quantity=form.stock_quantity.data,
            low_stock_threshold=form.low_stock_threshold.data,
            tax_rate=form.tax_rate.data,
            is_active=form.is_active.data
        )
        
        try:
            db.session.add(product)
            db.session.commit()
            flash(f'Product {product.name} created successfully!', 'success')
            return redirect(url_for('inventory.products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating product: {str(e)}', 'error')
    
    return render_template('inventory/product_form.html', form=form, title='New Product')

@inventory_bp.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    if not current_user.has_permission('write_inventory') and not current_user.has_permission('all'):
        flash('You do not have permission to edit products.', 'error')
        return redirect(url_for('inventory.products'))
    
    product = Product.query.get_or_404(id)
    form = ProductForm(product=product, obj=product)
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.description = form.description.data
        product.sku = form.sku.data
        product.barcode = form.barcode.data
        product.category_id = form.category_id.data
        product.cost_price = form.cost_price.data
        product.selling_price = form.selling_price.data
        product.stock_quantity = form.stock_quantity.data
        product.low_stock_threshold = form.low_stock_threshold.data
        product.tax_rate = form.tax_rate.data
        product.is_active = form.is_active.data
        
        try:
            db.session.commit()
            flash(f'Product {product.name} updated successfully!', 'success')
            return redirect(url_for('inventory.products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'error')
    
    return render_template('inventory/product_form.html', form=form, title='Edit Product', product=product)

@inventory_bp.route('/products/<int:id>/delete', methods=['POST'])
@login_required
def delete_product(id):
    if not current_user.has_permission('write_inventory') and not current_user.has_permission('all'):
        flash('You do not have permission to delete products.', 'error')
        return redirect(url_for('inventory.products'))
    
    product = Product.query.get_or_404(id)
    
    if product.sale_items:
        flash('Cannot delete product with existing sales records.', 'error')
        return redirect(url_for('inventory.products'))
    
    try:
        db.session.delete(product)
        db.session.commit()
        flash(f'Product {product.name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting product: {str(e)}', 'error')
    
    return redirect(url_for('inventory.products'))

@inventory_bp.route('/low-stock')
@login_required
def low_stock():
    products = Product.query.filter(
        Product.is_active == True,
        Product.stock_quantity <= Product.low_stock_threshold
    ).all()
    
    return render_template('inventory/low_stock.html', products=products)
