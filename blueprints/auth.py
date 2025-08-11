from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from forms import LoginForm
from models import User
from app import db
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # Handle success and error messages from query parameters
    success_msg = request.args.get('success')
    error_msg = request.args.get('error')
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            if user.is_active:
                login_user(user)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))
            else:
                return render_template('auth/login.html', form=form, 
                                     error_message='Your account has been deactivated. Please contact an administrator.')
        else:
            return render_template('auth/login.html', form=form,
                                 error_message='Invalid username or password.')
    
    return render_template('auth/login.html', form=form, 
                         success_message=success_msg, error_message=error_msg)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login', success='You have been logged out successfully.'))
