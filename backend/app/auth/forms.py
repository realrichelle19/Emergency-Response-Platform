"""
Authentication forms for the Emergency Response Platform.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models import User
from app.auth.utils import validate_password_strength

class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required')
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    """User registration form."""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address'),
        Length(max=255, message='Email must be less than 255 characters')
    ])
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required'),
        Length(min=1, max=100, message='First name must be between 1 and 100 characters')
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required'),
        Length(min=1, max=100, message='Last name must be between 1 and 100 characters')
    ])
    phone = StringField('Phone Number', validators=[
        Length(max=20, message='Phone number must be less than 20 characters')
    ])
    role = SelectField('Role', choices=[
        ('volunteer', 'Volunteer'),
        ('authority', 'Authority (NGO/Government/Disaster Team)')
    ], validators=[
        DataRequired(message='Please select a role')
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')
    
    def validate_email(self, email):
        """Check if email is already registered."""
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('This email address is already registered. Please use a different email.')
    
    def validate_password(self, password):
        """Validate password strength."""
        errors = validate_password_strength(password.data)
        if errors:
            raise ValidationError(' '.join(errors))

class ChangePasswordForm(FlaskForm):
    """Change password form for authenticated users."""
    current_password = PasswordField('Current Password', validators=[
        DataRequired(message='Current password is required')
    ])
    new_password = PasswordField('New Password', validators=[
        DataRequired(message='New password is required'),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    new_password2 = PasswordField('Confirm New Password', validators=[
        DataRequired(message='Please confirm your new password'),
        EqualTo('new_password', message='Passwords must match')
    ])
    submit = SubmitField('Change Password')
    
    def validate_new_password(self, new_password):
        """Validate new password strength."""
        errors = validate_password_strength(new_password.data)
        if errors:
            raise ValidationError(' '.join(errors))

class RequestPasswordResetForm(FlaskForm):
    """Request password reset form."""
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    submit = SubmitField('Request Password Reset')
    
    def validate_email(self, email):
        """Check if email exists in the system."""
        user = User.query.filter_by(email=email.data.lower()).first()
        if not user:
            raise ValidationError('No account found with this email address.')

class ResetPasswordForm(FlaskForm):
    """Reset password form."""
    password = PasswordField('New Password', validators=[
        DataRequired(message='Password is required'),
        Length(min=8, message='Password must be at least 8 characters long')
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(message='Please confirm your password'),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Reset Password')
    
    def validate_password(self, password):
        """Validate password strength."""
        errors = validate_password_strength(password.data)
        if errors:
            raise ValidationError(' '.join(errors))