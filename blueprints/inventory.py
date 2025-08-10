from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from forms import ProductForm, CategoryForm
from models import Product, Category, Store, StoreStock
from app import db
from utils import generate_sku
from datetime import datetime

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
    
    # Populate category choices
    categories = Category.query.filter_by(is_active=True).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    
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
            db.session.flush()  # Get the product ID
            
            # Initialize stock for all active stores
            stores = Store.query.filter_by(is_active=True).all()
            for store in stores:
                store_stock = StoreStock(
                    store_id=store.id,
                    product_id=product.id,
                    quantity=form.stock_quantity.data
                )
                db.session.add(store_stock)
            
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
    
    # Populate category choices
    categories = Category.query.filter_by(is_active=True).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    
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

@inventory_bp.route('/products/<int:id>')
@login_required
def view_product(id):
    product = Product.query.get_or_404(id)
    return render_template('inventory/view_product.html', product=product)

@inventory_bp.route('/low-stock')
@login_required
def low_stock():
    products = Product.query.filter(
        Product.is_active == True,
        Product.stock_quantity <= Product.low_stock_threshold
    ).all()
    
    return render_template('inventory/low_stock.html', products=products)

@inventory_bp.route('/categories')
@login_required
def categories():
    page = request.args.get('page', 1, type=int)
    categories = Category.query.paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('inventory/categories.html', categories=categories)

@inventory_bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
def new_category():
    form = CategoryForm()
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            description=form.description.data,
            is_active=form.is_active.data
        )
        
        try:
            db.session.add(category)
            db.session.commit()
            flash(f'Category {category.name} created successfully!', 'success')
            return redirect(url_for('inventory.categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating category: {str(e)}', 'error')
    
    return render_template('inventory/category_form.html', form=form, title='New Category')

@inventory_bp.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.description = form.description.data
        category.is_active = form.is_active.data
        
        try:
            db.session.commit()
            flash(f'Category {category.name} updated successfully!', 'success')
            return redirect(url_for('inventory.categories'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating category: {str(e)}', 'error')
    
    return render_template('inventory/category_form.html', form=form, title='Edit Category', category=category)

@inventory_bp.route('/categories/<int:id>/delete', methods=['POST'])
@login_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    
    if category.products:
        flash('Cannot delete category with existing products.', 'error')
        return redirect(url_for('inventory.categories'))
    
    try:
        db.session.delete(category)
        db.session.commit()
        flash(f'Category {category.name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting category: {str(e)}', 'error')
    
    return redirect(url_for('inventory.categories'))

# Product Image Management
@inventory_bp.route('/products/<int:product_id>/images')
@login_required
def product_images(product_id):
    """Manage product images"""
    product = Product.query.get_or_404(product_id)
    return render_template('inventory/product_images.html', product=product)

@inventory_bp.route('/products/<int:product_id>/upload-image', methods=['POST'])
@login_required
def upload_product_image(product_id):
    """Upload a new product image"""
    from models import ProductImage
    import os
    from werkzeug.utils import secure_filename
    
    if not current_user.has_permission('write_inventory') and not current_user.has_permission('all'):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    product = Product.query.get_or_404(product_id)
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    # Check file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return jsonify({'success': False, 'message': 'Invalid file type'}), 400
    
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join('static', 'uploads', 'products')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        filename = secure_filename(f"product_{product_id}_{int(datetime.now().timestamp())}_{file.filename}")
        file_path = os.path.join(upload_dir, filename)
        
        # Save file
        file.save(file_path)
        
        # Create database record
        is_primary = request.form.get('is_primary') == 'on'
        
        # If this is set as primary, remove primary flag from other images
        if is_primary:
            ProductImage.query.filter_by(product_id=product_id, is_primary=True).update({'is_primary': False})
        
        # If no images exist, make this the primary
        if not ProductImage.query.filter_by(product_id=product_id).first():
            is_primary = True
        
        product_image = ProductImage(
            product_id=product_id,
            image_url=f"/static/uploads/products/{filename}",
            is_primary=is_primary,
            alt_text=request.form.get('alt_text', '')
        )
        
        db.session.add(product_image)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Image uploaded successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error uploading image: {str(e)}'}), 500

@inventory_bp.route('/images/<int:image_id>/set-primary', methods=['POST'])
@login_required
def set_primary_image(image_id):
    """Set an image as primary"""
    from models import ProductImage
    
    if not current_user.has_permission('write_inventory') and not current_user.has_permission('all'):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    try:
        image = ProductImage.query.get_or_404(image_id)
        
        # Remove primary flag from other images of this product
        ProductImage.query.filter_by(product_id=image.product_id, is_primary=True).update({'is_primary': False})
        
        # Set this image as primary
        image.is_primary = True
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Primary image updated'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error setting primary image: {str(e)}'}), 500

@inventory_bp.route('/images/<int:image_id>/delete', methods=['DELETE'])
@login_required
def delete_product_image(image_id):
    """Delete a product image"""
    from models import ProductImage
    import os
    
    if not current_user.has_permission('write_inventory') and not current_user.has_permission('all'):
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    try:
        image = ProductImage.query.get_or_404(image_id)
        
        # Delete file from filesystem
        if image.image_url.startswith('/static/'):
            file_path = image.image_url[1:]  # Remove leading slash
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # If this was the primary image, set another image as primary
        if image.is_primary:
            other_image = ProductImage.query.filter(
                ProductImage.product_id == image.product_id,
                ProductImage.id != image_id
            ).first()
            if other_image:
                other_image.is_primary = True
        
        db.session.delete(image)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Image deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error deleting image: {str(e)}'}), 500
