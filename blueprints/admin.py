from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models import User, Category, CompanyProfile, AuditLog, SaleReturn, SaleReturnItem, Store, UserStore, Product
from forms import UserForm, CategoryForm, CompanyProfileForm, UserStoreAssignmentForm
from app import db
from utils import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    form = UserForm()
    
    # Populate store choices
    stores = Store.query.filter_by(is_active=True).all()
    form.store_id.choices = [(0, '--- No Store ---')] + [(s.id, s.name) for s in stores]
    
    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        user.store_id = form.store_id.data if form.store_id.data != 0 else None
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash(f'User {user.username} created successfully!', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'error')
    
    return render_template('admin/user_form.html', form=form, title='New User')

@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(id):
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    
    # Security checks: Regular admin cannot edit Super Admin or another admin's password/username
    is_editing_super_admin = user.role == 'Super Admin' and current_user.role != 'Super Admin'
    is_editing_other_admin = user.role in ['Admin', 'Super Admin'] and user.id != current_user.id
    
    # Block regular admins from editing Super Admin accounts
    if is_editing_super_admin:
        flash('You cannot edit Super Admin accounts.', 'error')
        return redirect(url_for('admin.users'))
    
    # Populate store choices
    stores = Store.query.filter_by(is_active=True).all()
    form.store_id.choices = [(0, '--- No Store ---')] + [(s.id, s.name) for s in stores]
    
    # Set current store selection
    if user.store_id:
        form.store_id.data = user.store_id
    else:
        form.store_id.data = 0
    
    # Password is optional for edits, but restricted for other admins
    form.password.validators = []
    
    if form.validate_on_submit():
        # Admins cannot edit usernames of other admins (including Super Admins)
        if is_editing_other_admin and form.username.data != user.username:
            flash('You cannot change the username of other admin accounts.', 'error')
            return render_template('admin/user_form.html', form=form, title='Edit User', user=user, is_editing_other_admin=is_editing_other_admin)
        
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        user.store_id = form.store_id.data if form.store_id.data != 0 else None
        
        # Only allow password changes if not editing another admin
        if form.password.data and not is_editing_other_admin:
            user.set_password(form.password.data)
        elif form.password.data and is_editing_other_admin:
            flash('You cannot change another admin\'s password.', 'error')
            return render_template('admin/user_form.html', form=form, title='Edit User', user=user, is_editing_other_admin=is_editing_other_admin)
        
        try:
            db.session.commit()
            flash(f'User {user.username} updated successfully!', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    return render_template('admin/user_form.html', form=form, title='Edit User', user=user, is_editing_other_admin=is_editing_other_admin)

@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    
    # Security checks: Cannot delete yourself, other admins, or Super Admins
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.users'))
    
    if user.role == 'Super Admin':
        flash('You cannot delete Super Admin accounts.', 'error')
        return redirect(url_for('admin.users'))
    
    if user.role == 'Admin' and current_user.role != 'Super Admin':
        flash('You cannot delete other admin accounts.', 'error')
        return redirect(url_for('admin.users'))
    
    try:
        # Handle related records before deleting user
        from models import CashRegister, UserStore, Sale, SaleItem
        
        # Delete all cash registers for this user (both open and closed)
        CashRegister.query.filter_by(user_id=user.id).delete()
        
        # Delete all sales made by this user
        user_sales = Sale.query.filter_by(user_id=user.id).all()
        for sale in user_sales:
            # Delete sale items first
            SaleItem.query.filter_by(sale_id=sale.id).delete()
            # Delete the sale
            db.session.delete(sale)
        
        # Remove user store assignments
        UserStore.query.filter_by(user_id=user.id).delete()
        
        # Now safe to delete the user
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/company-profile', methods=['GET', 'POST'])
@login_required
@admin_required
def company_profile():
    profile = CompanyProfile.query.first()
    if not profile:
        profile = CompanyProfile()
        profile.company_name = 'Your Company Name'
        db.session.add(profile)
        db.session.commit()
    
    form = CompanyProfileForm(obj=profile)
    if form.validate_on_submit():
        profile.company_name = form.company_name.data
        profile.address = form.address.data
        profile.phone = form.phone.data
        profile.email = form.email.data
        profile.website = form.website.data
        profile.tax_number = form.tax_number.data
        profile.registration_number = form.registration_number.data
        profile.default_currency = form.default_currency.data
        profile.default_tax_rate = form.default_tax_rate.data
        profile.receipt_footer = form.receipt_footer.data
        
        try:
            db.session.commit()
            flash('Company profile updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')
    
    return render_template('admin/company_profile.html', form=form, title='Company Profile')

@admin_bp.route('/categories-admin')
@login_required
@admin_required
def categories_admin():
    categories = Category.query.all()
    return render_template('admin/categories.html', categories=categories)

@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/user-stores')
@login_required
@admin_required
def user_stores():
    """List all user-store assignments"""
    # Get all users with their store assignments
    user_store_data = {}
    
    for user in User.query.all():
        user_stores = db.session.query(Store).join(UserStore).filter(UserStore.user_id == user.id).all()
        user_store_data[user.id] = {
            'user': user,
            'stores': user_stores
        }
    
    return render_template('admin/user_stores.html', user_store_data=user_store_data)

@admin_bp.route('/user-stores/assign', methods=['GET', 'POST'])
@login_required
@admin_required
def assign_user_stores():
    """Assign or reassign user to stores"""
    form = UserStoreAssignmentForm()
    
    # Populate form choices
    form.user_id.choices = [(u.id, f"{u.username} ({u.email})") for u in User.query.filter_by(is_active=True).all()]
    form.store_ids.choices = [(s.id, s.name) for s in Store.query.filter_by(is_active=True).all()]
    
    if form.validate_on_submit():
        user_id = form.user_id.data
        store_ids = form.store_ids.data
        
        try:
            # Remove existing assignments for this user
            UserStore.query.filter_by(user_id=user_id).delete()
            
            # Add new assignments
            user = User.query.get(user_id)
            if store_ids:
                primary_store_id = store_ids[0]  # Use first store as primary
                
                # Update user's direct store_id field for POS compatibility
                user.store_id = primary_store_id
                
                # Create UserStore entries for relationship tracking
                for store_id in store_ids:
                    user_store = UserStore()
                    user_store.user_id = user_id
                    user_store.store_id = store_id
                    # Mark first store as default
                    user_store.is_default = (store_id == primary_store_id)
                    db.session.add(user_store)
            else:
                # Clear user's direct store assignment
                user.store_id = None
            
            db.session.commit()
            
            if store_ids and user:
                stores = Store.query.filter(Store.id.in_(store_ids)).all()
                store_names = [store.name for store in stores]
                flash(f'User {user.username} assigned to stores: {", ".join(store_names)} (Primary: {stores[0].name})', 'success')
            else:
                flash(f'User store assignments cleared', 'success')
            return redirect(url_for('admin.user_stores'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error assigning user to stores: {str(e)}', 'error')
    
    return render_template('admin/user_store_assignment.html', form=form, title='Assign User to Stores')

@admin_bp.route('/user-stores/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user_stores(user_id):
    """Edit store assignments for a specific user"""
    user = User.query.get_or_404(user_id)
    form = UserStoreAssignmentForm()
    
    # Populate form choices
    form.user_id.choices = [(u.id, f"{u.username} ({u.email})") for u in User.query.filter_by(is_active=True).all()]
    form.store_ids.choices = [(s.id, s.name) for s in Store.query.filter_by(is_active=True).all()]
    
    if request.method == 'GET':
        # Pre-populate form with current assignments
        current_store_ids = [us.store_id for us in UserStore.query.filter_by(user_id=user_id).all()]
        form.user_id.data = user_id
        form.store_ids.data = current_store_ids
    
    if form.validate_on_submit():
        store_ids = form.store_ids.data
        
        try:
            # Remove existing assignments for this user
            UserStore.query.filter_by(user_id=user_id).delete()
            
            # Add new assignments
            if store_ids:
                primary_store_id = store_ids[0]  # Use first store as primary
                
                # Update user's direct store_id field for POS compatibility
                user.store_id = primary_store_id
                
                # Create UserStore entries for relationship tracking
                for store_id in store_ids:
                    user_store = UserStore()
                    user_store.user_id = user_id
                    user_store.store_id = store_id
                    # Mark first store as default
                    user_store.is_default = (store_id == primary_store_id)
                    db.session.add(user_store)
            else:
                # Clear user's direct store assignment
                user.store_id = None
            
            db.session.commit()
            
            if store_ids:
                stores = Store.query.filter(Store.id.in_(store_ids)).all()
                store_names = [store.name for store in stores]
                flash(f'Store assignments updated for {user.username}: {", ".join(store_names)} (Primary: {stores[0].name})', 'success')
            else:
                flash(f'All store assignments removed for {user.username}', 'success')
            return redirect(url_for('admin.user_stores'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating store assignments: {str(e)}', 'error')
    
    return render_template('admin/user_store_assignment.html', form=form, title=f'Edit Store Assignments - {user.username}', user=user)

@admin_bp.route('/returns')
@login_required
@admin_required
def returns():
    """Display returns management page"""
    from flask import jsonify
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    status = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = SaleReturn.query
    
    # Apply filters
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(SaleReturn.created_at >= start_dt)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(SaleReturn.created_at < end_dt)
        except ValueError:
            pass
            
    if status:
        query = query.filter(SaleReturn.status == status)
    
    # Get paginated results
    returns = query.order_by(SaleReturn.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Calculate summary stats
    total_amount = sum(r.return_amount for r in returns.items)
    pending_count = SaleReturn.query.filter_by(status='Pending').count()
    
    filters = {
        'start_date': start_date or '',
        'end_date': end_date or '',
        'status': status or ''
    }
    
    return render_template('admin/returns.html', 
                         returns=returns, 
                         filters=filters,
                         total_amount=total_amount,
                         pending_count=pending_count)

@admin_bp.route('/return/<int:return_id>/details')
@login_required
@admin_required
def return_details(return_id):
    """Get detailed information about a specific return"""
    from flask import jsonify
    
    sale_return = SaleReturn.query.get_or_404(return_id)
    
    # Build return details JSON
    return_data = {
        'id': sale_return.id,
        'return_number': sale_return.return_number,
        'created_at': sale_return.created_at.isoformat(),
        'original_receipt': sale_return.original_sale.receipt_number,
        'customer_name': sale_return.original_sale.customer.name if sale_return.original_sale.customer else None,
        'processed_by': sale_return.processed_by.full_name,
        'return_reason': sale_return.return_reason,
        'return_amount': float(sale_return.return_amount),
        'status': sale_return.status,
        'notes': sale_return.notes,
        'items': []
    }
    
    # Add return items
    for item in sale_return.return_items:
        return_data['items'].append({
            'product_name': item.product.name,
            'quantity_returned': item.quantity,
            'unit_price': float(item.unit_price),
            'total_amount': float(item.total_refund)
        })
    
    return jsonify(return_data)

@admin_bp.route('/return/<int:return_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_return(return_id):
    """Approve a pending return"""
    from flask import jsonify
    
    try:
        sale_return = SaleReturn.query.get_or_404(return_id)
        
        if sale_return.status != 'Pending':
            return jsonify({'error': 'Return is not in pending status'}), 400
        
        sale_return.status = 'Processed'
        sale_return.processed_at = datetime.utcnow()
        
        # Restore inventory for approved returns
        for item in sale_return.return_items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock_quantity += item.quantity
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Return {sale_return.return_number} approved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/return/<int:return_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_return(return_id):
    """Reject a pending return"""
    from flask import jsonify
    
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        sale_return = SaleReturn.query.get_or_404(return_id)
        
        if sale_return.status != 'Pending':
            return jsonify({'error': 'Return is not in pending status'}), 400
        
        sale_return.status = 'Rejected'
        sale_return.notes = f"{sale_return.notes or ''}\n\nREJECTED: {reason}".strip()
        
        # No inventory adjustment needed for rejection since inventory wasn't restored yet
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Return {sale_return.return_number} rejected'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500