from datetime import datetime, timezone
from app import db

class VolunteerProfile(db.Model):
    """Volunteer profile with location and availability information."""
    
    __tablename__ = 'volunteer_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    latitude = db.Column(db.Numeric(10, 8))
    longitude = db.Column(db.Numeric(11, 8))
    city = db.Column(db.String(100))
    availability_status = db.Column(db.Enum('available', 'busy', 'offline', 
                                          name='availability_statuses'), 
                                  default='offline', index=True)
    bio = db.Column(db.Text)
    interests = db.Column(db.Text)  # JSON string of interests
    experience_level = db.Column(db.Enum('beginner', 'intermediate', 'advanced', 'expert', 
                                       name='experience_levels'), default='beginner')
    languages_spoken = db.Column(db.Text)  # JSON string of languages
    emergency_contact_name = db.Column(db.String(200))
    emergency_contact_phone = db.Column(db.String(20))
    background_check_status = db.Column(db.Enum('not_required', 'pending', 'approved', 'rejected',
                                               name='background_check_statuses'), default='not_required')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    volunteer_skills = db.relationship('VolunteerSkill', backref='volunteer_profile', 
                                     cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', backref='volunteer_profile', 
                                cascade='all, delete-orphan')
    
    # Indexes for location-based queries
    __table_args__ = (
        db.Index('idx_location', 'latitude', 'longitude'),
        db.Index('idx_availability', 'availability_status'),
    )
    
    def __init__(self, **kwargs):
        super(VolunteerProfile, self).__init__(**kwargs)
    
    @property
    def is_available(self):
        """Check if volunteer is currently available."""
        return self.availability_status == 'available'
    
    @property
    def verified_skills(self):
        """Get list of verified skills."""
        return [vs for vs in self.volunteer_skills if vs.verification_status == 'verified']
    
    @property
    def pending_skills(self):
        """Get list of skills pending verification."""
        return [vs for vs in self.volunteer_skills if vs.verification_status == 'pending']
    
    @property
    def rejected_skills(self):
        """Get list of rejected skills."""
        return [vs for vs in self.volunteer_skills if vs.verification_status == 'rejected']
    
    @property
    def interests_list(self):
        """Get interests as a list."""
        if self.interests:
            import json
            try:
                return json.loads(self.interests)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @property
    def languages_list(self):
        """Get languages as a list."""
        if self.languages_spoken:
            import json
            try:
                return json.loads(self.languages_spoken)
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def set_interests(self, interests_list):
        """Set interests from a list."""
        import json
        self.interests = json.dumps(interests_list) if interests_list else None
    
    def set_languages(self, languages_list):
        """Set languages from a list."""
        import json
        self.languages_spoken = json.dumps(languages_list) if languages_list else None
    
    @property
    def rejected_skills(self):
        """Get list of rejected skills."""
        return [vs for vs in self.volunteer_skills if vs.verification_status == 'rejected']
    
    def has_verified_skill(self, skill_id):
        """Check if volunteer has a specific verified skill."""
        return any(vs.skill_id == skill_id and vs.verification_status == 'verified' 
                  for vs in self.volunteer_skills)
    
    def has_any_verified_skills(self, skill_ids):
        """Check if volunteer has any of the specified verified skills."""
        return any(self.has_verified_skill(skill_id) for skill_id in skill_ids)
    
    def get_distance_from(self, latitude, longitude):
        """Calculate distance from given coordinates using Haversine formula."""
        if not self.latitude or not self.longitude:
            return None
            
        import math
        
        # Convert to radians
        lat1_rad = math.radians(float(self.latitude))
        lon1_rad = math.radians(float(self.longitude))
        lat2_rad = math.radians(latitude)
        lon2_rad = math.radians(longitude)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        # Earth's radius in kilometers
        R = 6371
        distance = R * c
        
        return round(distance, 2)
    
    def to_dict(self, include_user=False):
        """Convert volunteer profile to dictionary representation."""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'city': self.city,
            'availability_status': self.availability_status,
            'bio': self.bio,
            'is_available': self.is_available,
            'verified_skills_count': len(self.verified_skills),
            'pending_skills_count': len(self.pending_skills),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_user and self.user:
            data['user'] = self.user.to_dict()
            
        return data
    
    def __repr__(self):
        return f'<VolunteerProfile {self.user.full_name if self.user else self.user_id}>'

class Skill(db.Model):
    """Master table of available skills."""
    
    __tablename__ = 'skills'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.Enum('medical', 'rescue', 'logistics', 'technical', 
                               'communication', 'other', name='skill_categories'), 
                        nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    volunteer_skills = db.relationship('VolunteerSkill', backref='skill', 
                                     cascade='all, delete-orphan')
    emergency_required_skills = db.relationship('EmergencyRequiredSkill', backref='skill',
                                               cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        super(Skill, self).__init__(**kwargs)
    
    @staticmethod
    def get_by_category(category):
        """Get all skills in a specific category."""
        return Skill.query.filter_by(category=category).all()
    
    @staticmethod
    def search_by_name(query):
        """Search skills by name."""
        return Skill.query.filter(Skill.name.ilike(f'%{query}%')).all()
    
    def to_dict(self):
        """Convert skill to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Skill {self.name} ({self.category})>'

class VolunteerSkill(db.Model):
    """Junction table for volunteer skills with verification status."""
    
    __tablename__ = 'volunteer_skills'
    
    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteer_profiles.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    verification_status = db.Column(db.Enum('pending', 'verified', 'rejected', 
                                          name='verification_statuses'), 
                                  default='pending', index=True)
    verification_notes = db.Column(db.Text)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at = db.Column(db.DateTime)
    documents_path = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Unique constraint to prevent duplicate volunteer-skill combinations
    __table_args__ = (
        db.UniqueConstraint('volunteer_id', 'skill_id', name='unique_volunteer_skill'),
        db.Index('idx_verification_status', 'verification_status'),
        db.Index('idx_volunteer_verified', 'volunteer_id', 'verification_status'),
    )
    
    def __init__(self, **kwargs):
        super(VolunteerSkill, self).__init__(**kwargs)
    
    def approve(self, admin_user, notes=None):
        """Approve the skill verification."""
        self.verification_status = 'verified'
        self.verified_by = admin_user.id
        self.verified_at = datetime.now(timezone.utc)
        if notes:
            self.verification_notes = notes
    
    def reject(self, admin_user, notes=None):
        """Reject the skill verification."""
        self.verification_status = 'rejected'
        self.verified_by = admin_user.id
        self.verified_at = datetime.now(timezone.utc)
        if notes:
            self.verification_notes = notes
    
    @property
    def is_verified(self):
        """Check if skill is verified."""
        return self.verification_status == 'verified'
    
    @property
    def is_pending(self):
        """Check if skill is pending verification."""
        return self.verification_status == 'pending'
    
    @property
    def is_rejected(self):
        """Check if skill is rejected."""
        return self.verification_status == 'rejected'
    
    def to_dict(self, include_skill=False, include_volunteer=False):
        """Convert volunteer skill to dictionary representation."""
        data = {
            'id': self.id,
            'volunteer_id': self.volunteer_id,
            'skill_id': self.skill_id,
            'verification_status': self.verification_status,
            'verification_notes': self.verification_notes,
            'verified_by': self.verified_by,
            'verified_at': self.verified_at.isoformat() if self.verified_at else None,
            'documents_path': self.documents_path,
            'is_verified': self.is_verified,
            'is_pending': self.is_pending,
            'is_rejected': self.is_rejected,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_skill and self.skill:
            data['skill'] = self.skill.to_dict()
            
        if include_volunteer and self.volunteer_profile:
            data['volunteer'] = self.volunteer_profile.to_dict(include_user=True)
            
        return data
    
    def __repr__(self):
        return f'<VolunteerSkill {self.volunteer_id}:{self.skill_id} ({self.verification_status})>'