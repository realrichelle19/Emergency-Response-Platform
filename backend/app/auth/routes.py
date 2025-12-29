"""
Authentication routes for the Emergency Response Platform.
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, current_user
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ChangePasswordForm
from app.auth.utils import get_redirect_target, log_user_activity, get_client_ip, get_user_agent
from app.models import User, VolunteerProfile, ActivityLog

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Find user by email (case insensitive)
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'error')
                return render_template('auth/login.html', form=form)
            
            # Log successful login
            login_user(user, remember=form.remember_me.data)
            
            # Log activity
            ActivityLog.log_user_login(
                user=user,
                ip_address=get_client_ip(),
                user_agent=get_user_agent()
            )
            db.session.commit()
            
            flash(f'Welcome back, {user.first_name}!', 'success')
            
            # Redirect to appropriate dashboard or requested page
            next_page = get_redirect_target()
            if next_page:
                return redirect(next_page)
            
            # Role-based redirection
            if user.role == 'volunteer':
                return redirect(url_for('volunteer.dashboard'))
            elif user.role == 'authority':
                return redirect(url_for('authority.dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.', 'error')
    
    return render_template('auth/login.html', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    
    # Pre-select role if provided in URL
    role = request.args.get('role')
    if role in ['volunteer', 'authority'] and not form.role.data:
        form.role.data = role
    
    if form.validate_on_submit():
        # Create new user
        user = User(
            email=form.email.data.lower(),
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role=form.role.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Create volunteer profile if user is a volunteer
        if user.role == 'volunteer':
            volunteer_profile = VolunteerProfile(
                user_id=user.id,
                availability_status='offline'
            )
            db.session.add(volunteer_profile)
        
        # Log registration activity
        ActivityLog.log_action(
            user_id=user.id,
            action='registration',
            entity_type='user',
            entity_id=user.id,
            details={
                'email': user.email,
                'role': user.role,
                'registration_method': 'web_form'
            },
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        db.session.commit()
        
        flash(f'Registration successful! Welcome to the Emergency Response Platform, {user.first_name}.', 'success')
        
        # Automatically log in the new user
        login_user(user)
        
        # Redirect based on role
        if user.role == 'volunteer':
            flash('Please complete your volunteer profile to start receiving emergency notifications.', 'info')
            return redirect(url_for('volunteer.profile'))
        elif user.role == 'authority':
            flash('Your authority account is ready. You can now create emergency requests.', 'info')
            return redirect(url_for('authority.dashboard'))
        else:
            return redirect(url_for('main.index'))
    
    return render_template('auth/register.html', form=form)

@bp.route('/logout')
def logout():
    """User logout."""
    if current_user.is_authenticated:
        # Log logout activity
        ActivityLog.log_user_logout(
            user=current_user,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        db.session.commit()
        
        logout_user()
        flash('You have been logged out successfully.', 'info')
    
    return redirect(url_for('main.index'))

@bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change password for authenticated users."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html', form=form)
        
        # Update password
        current_user.set_password(form.new_password.data)
        
        # Log password change
        ActivityLog.log_action(
            user_id=current_user.id,
            action='password_change',
            entity_type='user',
            entity_id=current_user.id,
            details={'changed_via': 'web_form'},
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        db.session.commit()
        
        flash('Your password has been changed successfully.', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('auth/change_password.html', form=form)

@bp.route('/profile')
def profile():
    """User profile page."""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    return render_template('auth/profile.html', user=current_user)

# API endpoints for authentication
@bp.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for user login."""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Find user by email
    user = User.query.filter_by(email=data['email'].lower()).first()
    
    if user and user.check_password(data['password']):
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 403
        
        # Log successful login
        login_user(user, remember=data.get('remember', False))
        
        ActivityLog.log_user_login(
            user=user,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        db.session.commit()
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'redirect_url': get_dashboard_url(user.role)
        }), 200
    else:
        return jsonify({'error': 'Invalid email or password'}), 401

@bp.route('/api/logout', methods=['POST'])
def api_logout():
    """API endpoint for user logout."""
    if current_user.is_authenticated:
        ActivityLog.log_user_logout(
            user=current_user,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        db.session.commit()
        
        logout_user()
        return jsonify({'message': 'Logout successful'}), 200
    else:
        return jsonify({'error': 'Not authenticated'}), 401

@bp.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for user registration."""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['email', 'first_name', 'last_name', 'role', 'password']
    for field in required_fields:
        if not data or not data.get(field):
            return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400
    
    # Check if email already exists
    if User.query.filter_by(email=data['email'].lower()).first():
        return jsonify({'error': 'Email address is already registered'}), 409
    
    # Validate role
    if data['role'] not in ['volunteer', 'authority']:
        return jsonify({'error': 'Invalid role'}), 400
    
    try:
        # Create new user
        user = User(
            email=data['email'].lower(),
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            phone=data.get('phone', '').strip() or None,
            role=data['role']
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()
        
        # Create volunteer profile if needed
        if user.role == 'volunteer':
            volunteer_profile = VolunteerProfile(
                user_id=user.id,
                availability_status='offline'
            )
            db.session.add(volunteer_profile)
        
        # Log registration
        ActivityLog.log_action(
            user_id=user.id,
            action='registration',
            entity_type='user',
            entity_id=user.id,
            details={
                'email': user.email,
                'role': user.role,
                'registration_method': 'api'
            },
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        db.session.commit()
        
        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500

def get_dashboard_url(role):
    """Get dashboard URL for user role."""
    if role == 'volunteer':
        return url_for('volunteer.dashboard')
    elif role == 'authority':
        return url_for('authority.dashboard')
    elif role == 'admin':
        return url_for('admin.dashboard')
    else:
        return url_for('main.index')