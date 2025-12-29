from datetime import datetime, timezone
from app import db

class Assignment(db.Model):
    """Assignment model linking volunteers to emergency requests."""
    
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    emergency_id = db.Column(db.Integer, db.ForeignKey('emergency_requests.id'), nullable=False)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('volunteer_profiles.id'), nullable=False)
    status = db.Column(db.Enum('requested', 'accepted', 'declined', 'completed', 'cancelled',
                             name='assignment_statuses'), default='requested')
    assigned_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    responded_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    # Unique constraint to prevent duplicate assignments
    __table_args__ = (
        db.UniqueConstraint('emergency_id', 'volunteer_id', name='unique_assignment'),
        db.Index('idx_volunteer_status', 'volunteer_id', 'status'),
        db.Index('idx_emergency_status', 'emergency_id', 'status'),
    )
    
    def __init__(self, **kwargs):
        super(Assignment, self).__init__(**kwargs)
    
    @property
    def is_requested(self):
        """Check if assignment is in requested state."""
        return self.status == 'requested'
    
    @property
    def is_accepted(self):
        """Check if assignment is accepted."""
        return self.status == 'accepted'
    
    @property
    def is_declined(self):
        """Check if assignment is declined."""
        return self.status == 'declined'
    
    @property
    def is_completed(self):
        """Check if assignment is completed."""
        return self.status == 'completed'
    
    @property
    def is_cancelled(self):
        """Check if assignment is cancelled."""
        return self.status == 'cancelled'
    
    @property
    def is_active(self):
        """Check if assignment is active (accepted but not completed)."""
        return self.status == 'accepted'
    
    @property
    def response_time_minutes(self):
        """Calculate response time in minutes."""
        if self.responded_at and self.assigned_at:
            delta = self.responded_at - self.assigned_at
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def completion_time_minutes(self):
        """Calculate completion time in minutes."""
        if self.completed_at and self.responded_at:
            delta = self.completed_at - self.responded_at
            return int(delta.total_seconds() / 60)
        return None
    
    @property
    def total_time_minutes(self):
        """Calculate total time from assignment to completion in minutes."""
        if self.completed_at and self.assigned_at:
            delta = self.completed_at - self.assigned_at
            return int(delta.total_seconds() / 60)
        return None
    
    def accept(self, notes=None):
        """Accept the assignment."""
        self.status = 'accepted'
        self.responded_at = datetime.now(timezone.utc)
        if notes:
            self.notes = notes
        
        # Update emergency status if this was the last needed volunteer
        if self.emergency_request.volunteers_needed <= 1:
            self.emergency_request.status = 'assigned'
    
    def decline(self, notes=None):
        """Decline the assignment."""
        self.status = 'declined'
        self.responded_at = datetime.now(timezone.utc)
        if notes:
            self.notes = notes
    
    def complete(self, notes=None):
        """Mark assignment as completed."""
        if self.status != 'accepted':
            raise ValueError("Can only complete accepted assignments")
        
        self.status = 'completed'
        self.completed_at = datetime.now(timezone.utc)
        if notes:
            self.notes = notes
        
        # Check if all assignments for this emergency are completed
        emergency = self.emergency_request
        active_assignments = [a for a in emergency.assignments if a.is_active]
        
        if not active_assignments:
            emergency.status = 'completed'
    
    def cancel(self, notes=None):
        """Cancel the assignment."""
        self.status = 'cancelled'
        if notes:
            self.notes = notes
        
        # If this was an accepted assignment, update emergency status back to open
        if self.status == 'accepted':
            emergency = self.emergency_request
            if emergency.status == 'assigned':
                emergency.status = 'open'
    
    @staticmethod
    def get_volunteer_history(volunteer_id, limit=None):
        """Get assignment history for a volunteer."""
        query = Assignment.query.filter_by(volunteer_id=volunteer_id).order_by(
            Assignment.assigned_at.desc()
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_emergency_assignments(emergency_id):
        """Get all assignments for an emergency."""
        return Assignment.query.filter_by(emergency_id=emergency_id).order_by(
            Assignment.assigned_at.desc()
        ).all()
    
    @staticmethod
    def get_pending_assignments(volunteer_id):
        """Get pending assignments for a volunteer."""
        return Assignment.query.filter_by(
            volunteer_id=volunteer_id,
            status='requested'
        ).order_by(Assignment.assigned_at.desc()).all()
    
    @staticmethod
    def get_active_assignments(volunteer_id):
        """Get active assignments for a volunteer."""
        return Assignment.query.filter_by(
            volunteer_id=volunteer_id,
            status='accepted'
        ).order_by(Assignment.assigned_at.desc()).all()
    
    def to_dict(self, include_emergency=False, include_volunteer=False):
        """Convert assignment to dictionary representation."""
        data = {
            'id': self.id,
            'emergency_id': self.emergency_id,
            'volunteer_id': self.volunteer_id,
            'status': self.status,
            'is_requested': self.is_requested,
            'is_accepted': self.is_accepted,
            'is_declined': self.is_declined,
            'is_completed': self.is_completed,
            'is_cancelled': self.is_cancelled,
            'is_active': self.is_active,
            'notes': self.notes,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'response_time_minutes': self.response_time_minutes,
            'completion_time_minutes': self.completion_time_minutes,
            'total_time_minutes': self.total_time_minutes
        }
        
        if include_emergency and self.emergency_request:
            data['emergency'] = self.emergency_request.to_dict(include_authority=True, include_skills=True)
        
        if include_volunteer and self.volunteer_profile:
            data['volunteer'] = self.volunteer_profile.to_dict(include_user=True)
        
        return data
    
    def __repr__(self):
        return f'<Assignment {self.emergency_id}:{self.volunteer_id} ({self.status})>'