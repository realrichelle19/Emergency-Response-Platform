from datetime import datetime, timezone
from app import db
import json

class ActivityLog(db.Model):
    """Activity log model for audit trail of all user actions and system events."""
    
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Indexes for efficient querying
    __table_args__ = (
        db.Index('idx_user_action', 'user_id', 'action'),
        db.Index('idx_entity', 'entity_type', 'entity_id'),
        db.Index('idx_created_at', 'created_at'),
    )
    
    def __init__(self, **kwargs):
        super(ActivityLog, self).__init__(**kwargs)
    
    @staticmethod
    def log_action(user_id, action, entity_type, entity_id=None, details=None, 
                   ip_address=None, user_agent=None):
        """Create a new activity log entry."""
        log_entry = ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(log_entry)
        return log_entry
    
    @staticmethod
    def log_user_login(user, ip_address=None, user_agent=None):
        """Log user login action."""
        return ActivityLog.log_action(
            user_id=user.id,
            action='login',
            entity_type='user',
            entity_id=user.id,
            details={'email': user.email, 'role': user.role},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_user_logout(user, ip_address=None, user_agent=None):
        """Log user logout action."""
        return ActivityLog.log_action(
            user_id=user.id,
            action='logout',
            entity_type='user',
            entity_id=user.id,
            details={'email': user.email, 'role': user.role},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_profile_update(user, profile_data, ip_address=None, user_agent=None):
        """Log profile update action."""
        return ActivityLog.log_action(
            user_id=user.id,
            action='profile_update',
            entity_type='volunteer_profile',
            entity_id=user.volunteer_profile.id if user.volunteer_profile else None,
            details=profile_data,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_availability_change(user, old_status, new_status, ip_address=None, user_agent=None):
        """Log availability status change."""
        return ActivityLog.log_action(
            user_id=user.id,
            action='availability_change',
            entity_type='volunteer_profile',
            entity_id=user.volunteer_profile.id if user.volunteer_profile else None,
            details={'old_status': old_status, 'new_status': new_status},
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_skill_verification(admin_user, volunteer_skill, decision, notes=None, 
                              ip_address=None, user_agent=None):
        """Log skill verification decision."""
        return ActivityLog.log_action(
            user_id=admin_user.id,
            action='skill_verification',
            entity_type='volunteer_skill',
            entity_id=volunteer_skill.id,
            details={
                'volunteer_id': volunteer_skill.volunteer_id,
                'skill_id': volunteer_skill.skill_id,
                'decision': decision,
                'notes': notes
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_skill_verification_decision(admin_user, volunteer_skill, decision, notes=None, 
                                      ip_address=None, user_agent=None):
        """Log skill verification decision (alias for compatibility)."""
        return ActivityLog.log_skill_verification(
            admin_user, volunteer_skill, decision, notes, ip_address, user_agent
        )
    
    @staticmethod
    def log_emergency_creation(user, emergency, ip_address=None, user_agent=None):
        """Log emergency request creation."""
        return ActivityLog.log_action(
            user_id=user.id,
            action='emergency_creation',
            entity_type='emergency_request',
            entity_id=emergency.id,
            details={
                'title': emergency.title,
                'priority_level': emergency.priority_level,
                'required_volunteers': emergency.required_volunteers,
                'search_radius_km': emergency.search_radius_km
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_emergency_escalation(user, emergency, ip_address=None, user_agent=None):
        """Log emergency escalation."""
        return ActivityLog.log_action(
            user_id=user.id,
            action='emergency_escalation',
            entity_type='emergency_request',
            entity_id=emergency.id,
            details={
                'title': emergency.title,
                'old_priority': emergency.priority_level,
                'escalation_count': emergency.escalation_count,
                'search_radius_km': emergency.search_radius_km
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_assignment_acceptance(user, assignment, ip_address=None, user_agent=None):
        """Log assignment acceptance."""
        return ActivityLog.log_action(
            user_id=user.id,
            action='assignment_acceptance',
            entity_type='assignment',
            entity_id=assignment.id,
            details={
                'emergency_id': assignment.emergency_id,
                'emergency_title': assignment.emergency_request.title if assignment.emergency_request else None,
                'notes': assignment.notes
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_assignment_decline(user, assignment, ip_address=None, user_agent=None):
        """Log assignment decline."""
        return ActivityLog.log_action(
            user_id=user.id,
            action='assignment_decline',
            entity_type='assignment',
            entity_id=assignment.id,
            details={
                'emergency_id': assignment.emergency_id,
                'emergency_title': assignment.emergency_request.title if assignment.emergency_request else None,
                'notes': assignment.notes
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_assignment_cancellation(user, assignment, ip_address=None, user_agent=None):
        """Log assignment cancellation."""
        return ActivityLog.log_action(
            user_id=user.id,
            action='assignment_cancellation',
            entity_type='assignment',
            entity_id=assignment.id,
            details={
                'emergency_id': assignment.emergency_id,
                'emergency_title': assignment.emergency_request.title if assignment.emergency_request else None,
                'cancelled_by_role': user.role,
                'notes': assignment.notes
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_assignment_completion(user, assignment, ip_address=None, user_agent=None):
        """Log assignment completion."""
        return ActivityLog.log_action(
            user_id=user.id,
            action='assignment_completion',
            entity_type='assignment',
            entity_id=assignment.id,
            details={
                'emergency_id': assignment.emergency_id,
                'emergency_title': assignment.emergency_request.title if assignment.emergency_request else None,
                'total_time_minutes': assignment.total_time_minutes
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def log_user_block(admin_user, blocked_user, reason=None, ip_address=None, user_agent=None):
        """Log user blocking action."""
        return ActivityLog.log_action(
            user_id=admin_user.id,
            action='user_block',
            entity_type='user',
            entity_id=blocked_user.id,
            details={
                'blocked_email': blocked_user.email,
                'blocked_role': blocked_user.role,
                'reason': reason
            },
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    @staticmethod
    def get_user_activity(user_id, limit=None):
        """Get activity history for a specific user."""
        query = ActivityLog.query.filter_by(user_id=user_id).order_by(
            ActivityLog.created_at.desc()
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_entity_activity(entity_type, entity_id, limit=None):
        """Get activity history for a specific entity."""
        query = ActivityLog.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id
        ).order_by(ActivityLog.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_recent_activity(limit=50):
        """Get recent system activity."""
        return ActivityLog.query.order_by(
            ActivityLog.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_activity_by_action(action, limit=None):
        """Get activity by specific action type."""
        query = ActivityLog.query.filter_by(action=action).order_by(
            ActivityLog.created_at.desc()
        )
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    def to_dict(self, include_user=False):
        """Convert activity log to dictionary representation."""
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_user and self.user:
            data['user'] = {
                'id': self.user.id,
                'email': self.user.email,
                'full_name': self.user.full_name,
                'role': self.user.role
            }
        
        return data
    
    def __repr__(self):
        return f'<ActivityLog {self.action} on {self.entity_type}:{self.entity_id}>'