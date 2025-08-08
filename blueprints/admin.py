from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import User, Category, CompanyProfile, AuditLog, Store, UserStore
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
    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.role = form.role.data
        user.is_active = form.is_active.data
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
    form = UserForm(user=user, obj=user)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        
        if form.password.data:
            user.set_password(form.password.data)
        
        try:
            db.session.commit()
            flash(f'User {user.username} updated successfully!', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'error')
    
    return render_template('admin/user_form.html', form=form, title='Edit User', user=user)

@admin_bp.route('/users/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    user = User.query.get_or_404(id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.users'))
    
    try:
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
    
    if form.validate_on_submit():
        user_id = form.user_id.data
        store_ids = form.store_ids.data
        
        try:
            # Remove existing assignments for this user
            UserStore.query.filter_by(user_id=user_id).delete()
            
            # Add new assignments
            if store_ids:
                for store_id in store_ids:
                    user_store = UserStore()
                    user_store.user_id = user_id
                    user_store.store_id = store_id
                    db.session.add(user_store)
            
            db.session.commit()
            
            user = User.query.get(user_id)
            if store_ids and user:
                stores = Store.query.filter(Store.id.in_(store_ids)).all()
                store_names = [store.name for store in stores]
                flash(f'User {user.username} assigned to stores: {", ".join(store_names)}', 'success')
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
                for store_id in store_ids:
                    user_store = UserStore()
                    user_store.user_id = user_id
                    user_store.store_id = store_id
                    db.session.add(user_store)
            
            db.session.commit()
            
            if store_ids:
                stores = Store.query.filter(Store.id.in_(store_ids)).all()
                store_names = [store.name for store in stores]
                flash(f'Store assignments updated for {user.username}: {", ".join(store_names)}', 'success')
            else:
                flash(f'All store assignments removed for {user.username}', 'success')
            return redirect(url_for('admin.user_stores'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating store assignments: {str(e)}', 'error')
    
    return render_template('admin/user_store_assignment.html', form=form, title=f'Edit Store Assignments - {user.username}', user=user)