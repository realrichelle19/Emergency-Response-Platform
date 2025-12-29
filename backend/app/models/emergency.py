from datetime import datetime, timedelta, timezone
from app import db

class EmergencyRequest(db.Model):
    """Emergency request model with location and skill requirements."""
    
    __tablename__ = 'emergency_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    authority_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Numeric(10, 8), nullable=False)
    longitude = db.Column(db.Numeric(11, 8), nullable=False)
    address = db.Column(db.String(500))
    priority_level = db.Column(db.Enum('low', 'medium', 'high', 'critical', 
                                     name='priority_levels'), nullable=False)
    status = db.Column(db.Enum('open', 'assigned', 'completed', 'cancelled', 
                             name='emergency_statuses'), default='open', index=True)
    required_volunteers = db.Column(db.Integer, default=1)
    search_radius_km = db.Column(db.Integer, default=10)
    escalation_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime)
    
    # Relationships
    required_skills = db.relationship('EmergencyRequiredSkill', backref='emergency_request',
                                    cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', backref='emergency_request',
                                cascade='all, delete-orphan')
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('idx_location_priority', 'latitude', 'longitude', 'priority_level'),
        db.Index('idx_status_created', 'status', 'created_at'),
        db.Index('idx_authority', 'authority_id'),
    )
    
    def __init__(self, **kwargs):
        super(EmergencyRequest, self).__init__(**kwargs)
        # Set default expiration time if not provided
        if not self.expires_at:
            from flask import current_app
            timeout_minutes = current_app.config.get('ESCALATION_TIMEOUT_MINUTES', 30)
            self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
    
    @property
    def is_open(self):
        """Check if emergency is open."""
        return self.status == 'open'
    
    @property
    def is_assigned(self):
        """Check if emergency is assigned."""
        return self.status == 'assigned'
    
    @property
    def is_completed(self):
        """Check if emergency is completed."""
        return self.status == 'completed'
    
    @property
    def is_cancelled(self):
        """Check if emergency is cancelled."""
        return self.status == 'cancelled'
    
    @property
    def is_expired(self):
        """Check if emergency has expired."""
        return self.expires_at and datetime.now(timezone.utc) > self.expires_at
    
    @property
    def priority_score(self):
        """Get numeric priority score for sorting."""
        priority_scores = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        return priority_scores.get(self.priority_level, 1)
    
    @property
    def required_skill_ids(self):
        """Get list of required skill IDs."""
        return [rs.skill_id for rs in self.required_skills]
    
    @property
    def mandatory_skill_ids(self):
        """Get list of mandatory skill IDs."""
        return [rs.skill_id for rs in self.required_skills if rs.is_mandatory]
    
    @property
    def optional_skill_ids(self):
        """Get list of optional skill IDs."""
        return [rs.skill_id for rs in self.required_skills if not rs.is_mandatory]
    
    @property
    def accepted_assignments(self):
        """Get list of accepted assignments."""
        return [a for a in self.assignments if a.status == 'accepted']
    
    @property
    def pending_assignments(self):
        """Get list of pending assignments."""
        return [a for a in self.assignments if a.status == 'requested']
    
    @property
    def volunteers_needed(self):
        """Calculate how many more volunteers are needed."""
        accepted_count = len(self.accepted_assignments)
        return max(0, self.required_volunteers - accepted_count)
    
    def escalate(self):
        """Escalate the emergency priority and expand search radius."""
        self.escalation_count += 1
        
        # Increase priority level
        if self.priority_level == 'low':
            self.priority_level = 'medium'
        elif self.priority_level == 'medium':
            self.priority_level = 'high'
        elif self.priority_level == 'high':
            self.priority_level = 'critical'
        
        # Expand search radius
        from flask import current_app
        max_radius = current_app.config.get('MAX_SEARCH_RADIUS_KM', 100)
        new_radius = min(self.search_radius_km * 2, max_radius)
        self.search_radius_km = new_radius
        
        # Extend expiration time
        timeout_minutes = current_app.config.get('ESCALATION_TIMEOUT_MINUTES', 30)
        self.expires_at = datetime.now(timezone.utc) + timedelta(minutes=timeout_minutes)
        
        self.updated_at = datetime.now(timezone.utc)
    
    def get_distance_from_volunteer(self, volunteer_profile):
        """Calculate distance from volunteer location."""
        if not volunteer_profile.latitude or not volunteer_profile.longitude:
            return None
        return volunteer_profile.get_distance_from(float(self.latitude), float(self.longitude))
    
    def find_matching_volunteers(self, limit=None):
        """Find volunteers that match this emergency's requirements."""
        from app.models.volunteer import VolunteerProfile, VolunteerSkill
        from sqlalchemy import and_, func
        
        # Base query for available volunteers within radius
        query = db.session.query(VolunteerProfile).filter(
            VolunteerProfile.availability_status == 'available',
            VolunteerProfile.latitude.isnot(None),
            VolunteerProfile.longitude.isnot(None)
        )
        
        # Add distance filter using Haversine formula
        lat_rad = func.radians(self.latitude)
        lon_rad = func.radians(self.longitude)
        vol_lat_rad = func.radians(VolunteerProfile.latitude)
        vol_lon_rad = func.radians(VolunteerProfile.longitude)
        
        # Haversine distance calculation
        distance = (
            6371 * func.acos(
                func.cos(lat_rad) * func.cos(vol_lat_rad) *
                func.cos(vol_lon_rad - lon_rad) +
                func.sin(lat_rad) * func.sin(vol_lat_rad)
            )
        )
        
        query = query.filter(distance <= self.search_radius_km)
        
        # Filter by required skills if any
        if self.required_skill_ids:
            # Volunteers must have at least one verified required skill
            query = query.join(VolunteerSkill).filter(
                and_(
                    VolunteerSkill.skill_id.in_(self.required_skill_ids),
                    VolunteerSkill.verification_status == 'verified'
                )
            ).distinct()
        
        # Order by priority: distance and verification level
        query = query.add_columns(distance.label('distance')).order_by('distance')
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def to_dict(self, include_authority=False, include_skills=False, include_assignments=False):
        """Convert emergency request to dictionary representation."""
        data = {
            'id': self.id,
            'authority_id': self.authority_id,
            'title': self.title,
            'description': self.description,
            'latitude': float(self.latitude),
            'longitude': float(self.longitude),
            'address': self.address,
            'priority_level': self.priority_level,
            'priority_score': self.priority_score,
            'status': self.status,
            'required_volunteers': self.required_volunteers,
            'search_radius_km': self.search_radius_km,
            'escalation_count': self.escalation_count,
            'volunteers_needed': self.volunteers_needed,
            'is_open': self.is_open,
            'is_assigned': self.is_assigned,
            'is_completed': self.is_completed,
            'is_expired': self.is_expired,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
        
        if include_authority and self.authority:
            data['authority'] = self.authority.to_dict()
        
        if include_skills:
            data['required_skills'] = [rs.to_dict(include_skill=True) for rs in self.required_skills]
        
        if include_assignments:
            data['assignments'] = [a.to_dict(include_volunteer=True) for a in self.assignments]
        
        return data
    
    def __repr__(self):
        return f'<EmergencyRequest {self.title} ({self.priority_level})>'

class EmergencyRequiredSkill(db.Model):
    """Junction table for emergency required skills."""
    
    __tablename__ = 'emergency_required_skills'
    
    id = db.Column(db.Integer, primary_key=True)
    emergency_id = db.Column(db.Integer, db.ForeignKey('emergency_requests.id'), nullable=False)
    skill_id = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    is_mandatory = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Unique constraint to prevent duplicate emergency-skill combinations
    __table_args__ = (
        db.UniqueConstraint('emergency_id', 'skill_id', name='unique_emergency_skill'),
    )
    
    def __init__(self, **kwargs):
        super(EmergencyRequiredSkill, self).__init__(**kwargs)
    
    def to_dict(self, include_skill=False, include_emergency=False):
        """Convert emergency required skill to dictionary representation."""
        data = {
            'id': self.id,
            'emergency_id': self.emergency_id,
            'skill_id': self.skill_id,
            'is_mandatory': self.is_mandatory,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_skill and self.skill:
            data['skill'] = self.skill.to_dict()
        
        if include_emergency and self.emergency_request:
            data['emergency'] = self.emergency_request.to_dict()
        
        return data
    
    def __repr__(self):
        return f'<EmergencyRequiredSkill {self.emergency_id}:{self.skill_id} ({"mandatory" if self.is_mandatory else "optional"})>'