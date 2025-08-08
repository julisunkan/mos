from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from forms import CustomerForm
from models import Customer, Sale
from app import db

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    customer_type = request.args.get('type', '')
    
    query = Customer.query
    
    if search:
        query = query.filter(
            db.or_(
                Customer.name.ilike(f'%{search}%'),
                Customer.email.ilike(f'%{search}%'),
                Customer.phone.ilike(f'%{search}%')
            )
        )
    
    if customer_type:
        query = query.filter_by(customer_type=customer_type)
    
    customers = query.paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('customers/index.html', 
                         customers=customers,
                         search=search,
                         selected_type=customer_type)

@customers_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_customer():
    if not current_user.has_permission('write_customers') and not current_user.has_permission('all'):
        flash('You do not have permission to create customers.', 'error')
        return redirect(url_for('customers.index'))
    
    form = CustomerForm()
    if form.validate_on_submit():
        customer = Customer(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            address=form.address.data,
            customer_type=form.customer_type.data,
            credit_limit=form.credit_limit.data,
            is_active=form.is_active.data
        )
        
        try:
            db.session.add(customer)
            db.session.commit()
            flash(f'Customer {customer.name} created successfully!', 'success')
            return redirect(url_for('customers.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating customer: {str(e)}', 'error')
    
    return render_template('customers/customer_form.html', form=form, title='New Customer')

@customers_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(id):
    if not current_user.has_permission('write_customers') and not current_user.has_permission('all'):
        flash('You do not have permission to edit customers.', 'error')
        return redirect(url_for('customers.index'))
    
    customer = Customer.query.get_or_404(id)
    form = CustomerForm(customer=customer, obj=customer)
    
    if form.validate_on_submit():
        customer.name = form.name.data
        customer.email = form.email.data
        customer.phone = form.phone.data
        customer.address = form.address.data
        customer.customer_type = form.customer_type.data
        customer.credit_limit = form.credit_limit.data
        customer.is_active = form.is_active.data
        
        try:
            db.session.commit()
            flash(f'Customer {customer.name} updated successfully!', 'success')
            return redirect(url_for('customers.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating customer: {str(e)}', 'error')
    
    return render_template('customers/customer_form.html', form=form, title='Edit Customer', customer=customer)

@customers_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_customer(id):
    if not current_user.has_permission('write_customers') and not current_user.has_permission('all'):
        flash('You do not have permission to delete customers.', 'error')
        return redirect(url_for('customers.index'))
    
    customer = Customer.query.get_or_404(id)
    
    if customer.sales:
        flash('Cannot delete customer with existing sales records.', 'error')
        return redirect(url_for('customers.index'))
    
    try:
        db.session.delete(customer)
        db.session.commit()
        flash(f'Customer {customer.name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting customer: {str(e)}', 'error')
    
    return redirect(url_for('customers.index'))

@customers_bp.route('/<int:id>')
@login_required
def view_customer(id):
    customer = Customer.query.get_or_404(id)
    
    # Get customer's sales history
    page = request.args.get('page', 1, type=int)
    sales = Sale.query.filter_by(customer_id=id).order_by(
        Sale.created_at.desc()
    ).paginate(page=page, per_page=10, error_out=False)
    
    # Calculate total spent
    total_spent = db.session.query(db.func.sum(Sale.total_amount)).filter_by(customer_id=id).scalar() or 0
    
    return render_template('customers/view.html', 
                         customer=customer, 
                         sales=sales,
                         total_spent=total_spent)
