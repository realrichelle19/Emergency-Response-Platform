from flask import render_template, redirect, url_for
from flask_login import current_user
from app.main import bp

@bp.route('/')
def index():
    """Main landing page."""
    if current_user.is_authenticated:
        # Redirect to appropriate dashboard based on role
        if current_user.role == 'volunteer':
            return redirect(url_for('volunteer.dashboard'))
        elif current_user.role == 'authority':
            return redirect(url_for('authority.dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
    
    return render_template('index.html')

@bp.route('/about')
def about():
    """About page."""
    return render_template('about.html')