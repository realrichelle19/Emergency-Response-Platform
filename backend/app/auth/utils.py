"""
Authentication utilities and decorators for the Emergency Response Platform.
"""

from functools import wraps
from flask import abort, request, jsonify
from flask_login import current_user
import bcrypt
from app.models.activity_log import ActivityLog

def hash_password(password):
    """Hash a password using bcrypt."""
    if isinstance(password, str):
        password = password.encode('utf-8')
    
    # Generate salt and hash password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password, salt)
    
    return hashed.decode('utf-8')

def check_password(password, hashed_password):
    """Check if a password matches the hashed password."""
    if isinstance(password, str):
        password = password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    
    return bcrypt.checkpw(password, hashed_password)

def require_role(required_role):
    """Decorator to require a specific user role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                abort(401)
            
            if current_user.role != required_role:
                if request.is_json:
                    return jsonify({'error': f'Role {required_role} required'}), 403
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_roles(*required_roles):
    """Decorator to require one of multiple user roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                abort(401)
            
            if current_user.role not in required_roles:
                if request.is_json:
                    return jsonify({'error': f'One of roles {required_roles} required'}), 403
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_volunteer():
    """Decorator to require volunteer role."""
    return require_role('volunteer')

def require_authority():
    """Decorator to require authority role."""
    return require_role('authority')

def require_admin():
    """Decorator to require admin role."""
    return require_role('admin')

def require_volunteer_or_admin():
    """Decorator to require volunteer or admin role."""
    return require_roles('volunteer', 'admin')

def require_authority_or_admin():
    """Decorator to require authority or admin role."""
    return require_roles('authority', 'admin')

def log_user_activity(action, entity_type, entity_id=None, details=None):
    """Log user activity for audit trail."""
    if current_user.is_authenticated:
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent')
        
        ActivityLog.log_action(
            user_id=current_user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

def get_client_ip():
    """Get client IP address from request."""
    return request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)

def get_user_agent():
    """Get user agent from request."""
    return request.headers.get('User-Agent', '')

def validate_password_strength(password):
    """Validate password strength requirements."""
    errors = []
    
    if len(password) < 8:
        errors.append('Password must be at least 8 characters long')
    
    if not any(c.isupper() for c in password):
        errors.append('Password must contain at least one uppercase letter')
    
    if not any(c.islower() for c in password):
        errors.append('Password must contain at least one lowercase letter')
    
    if not any(c.isdigit() for c in password):
        errors.append('Password must contain at least one number')
    
    # Check for special characters
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if not any(c in special_chars for c in password):
        errors.append('Password must contain at least one special character')
    
    return errors

def is_safe_url(target):
    """Check if a URL is safe for redirects."""
    from urllib.parse import urlparse, urljoin
    from flask import request, url_for
    
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

def get_redirect_target():
    """Get safe redirect target from request."""
    for target in request.values.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target
    return None