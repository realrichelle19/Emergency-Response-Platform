from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager

class User(UserMixin, db.Model):
    """Base user model for all user types (volunteer, authority, admin)."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('volunteer', 'authority', 'admin', name='user_roles'), 
                     nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    volunteer_profile = db.relationship('VolunteerProfile', backref='user', uselist=False, 
                                      cascade='all, delete-orphan')
    created_emergencies = db.relationship('EmergencyRequest', backref='authority', 
                                        cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='user', cascade='all, delete-orphan')
    verified_skills = db.relationship('VolunteerSkill', foreign_keys='VolunteerSkill.verified_by',
                                    backref='verifier')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check if the provided password matches the user's password."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def is_volunteer(self):
        """Check if user is a volunteer."""
        return self.role == 'volunteer'
    
    def is_authority(self):
        """Check if user is an authority."""
        return self.role == 'authority'
    
    def is_admin(self):
        """Check if user is an admin."""
        return self.role == 'admin'
    
    def can_access_volunteer_features(self):
        """Check if user can access volunteer features."""
        return self.role == 'volunteer'
    
    def can_access_authority_features(self):
        """Check if user can access authority features."""
        return self.role == 'authority'
    
    def can_access_admin_features(self):
        """Check if user can access admin features."""
        return self.role == 'admin'
    
    def to_dict(self):
        """Convert user to dictionary representation."""
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'phone': self.phone,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))