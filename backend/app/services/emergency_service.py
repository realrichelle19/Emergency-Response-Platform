"""
Emergency request management service for the Emergency Response Platform.

This module provides comprehensive emergency request management including
creation, status tracking, escalation, and volunteer assignment coordination.
"""

from typing import List, Dict, Optional, Tuple
from flask import current_app
from app import db
from app.models import EmergencyRequest, EmergencyRequiredSkill, Assignment, Skill, ActivityLog
from app.services.location_service import LocationService
from app.services.matching_service import MatchingService
from app.auth.utils import log_user_activity
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

class EmergencyService:
    """Service class for emergency request management."""
    
    @staticmethod
    def create_emergency_request(authority_user, emergency_data, required_skill_ids=None):
        """
        Create a new emergency request with required skills.
        
        Args:
            authority_user: The authority user creating the request
            emergency_data: Dictionary with emergency details
            required_skill_ids: List of required skill IDs
            
        Returns:
            Created EmergencyRequest object
        """
        try:
            # Validate coordinates
            if not LocationService.validate_coordinates(
                emergency_data['latitude'], emergency_data['longitude']
            ):
                raise ValueError("Invalid coordinates provided")
            
            # Create emergency request
            emergency = EmergencyRequest(
                authority_id=authority_user.id,
                title=emergency_data['title'],
                description=emergency_data['description'],
                latitude=emergency_data['latitude'],
                longitude=emergency_data['longitude'],
                address=emergency_data.get('address'),
                priority_level=emergency_data['priority_level'],
                required_volunteers=emergency_data.get('required_volunteers', 1),
                search_radius_km=emergency_data.get('search_radius_km', 
                    current_app.config.get('DEFAULT_SEARCH_RADIUS_KM', 10))
            )
            
            db.session.add(emergency)
            db.session.flush()  # Get emergency ID
            
            # Add required skills
            if required_skill_ids:
                for skill_id in required_skill_ids:
                    # Verify skill exists
                    skill = db.session.get(Skill, skill_id)
                    if not skill:
                        raise ValueError(f"Skill with ID {skill_id} does not exist")
                    
                    required_skill = EmergencyRequiredSkill(
                        emergency_id=emergency.id,
                        skill_id=skill_id,
                        is_mandatory=True  # Default to mandatory, can be customized later
                    )
                    db.session.add(required_skill)
            
            db.session.commit()
            
            # Log activity
            ActivityLog.log_emergency_creation(
                user=authority_user,
                emergency=emergency
            )
            
            # Automatically start volunteer matching
            EmergencyService.initiate_volunteer_matching(emergency)
            
            return emergency
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def update_emergency_request(emergency_id, authority_user, update_data):
        """
        Update an existing emergency request.
        
        Args:
            emergency_id: ID of the emergency to update
            authority_user: The authority user making the update
            update_data: Dictionary with fields to update
            
        Returns:
            Updated EmergencyRequest object
        """
        try:
            emergency = EmergencyRequest.query.filter_by(
                id=emergency_id,
                authority_id=authority_user.id
            ).first()
            
            if not emergency:
                raise ValueError("Emergency request not found or access denied")
            
            if emergency.status in ['completed', 'cancelled']:
                raise ValueError("Cannot update completed or cancelled emergency")
            
            # Update allowed fields
            updatable_fields = [
                'title', 'description', 'address', 'priority_level', 
                'required_volunteers', 'search_radius_km'
            ]
            
            for field in updatable_fields:
                if field in update_data:
                    setattr(emergency, field, update_data[field])
            
            # Validate coordinates if being updated
            if 'latitude' in update_data or 'longitude' in update_data:
                lat = update_data.get('latitude', emergency.latitude)
                lon = update_data.get('longitude', emergency.longitude)
                
                if not LocationService.validate_coordinates(lat, lon):
                    raise ValueError("Invalid coordinates provided")
                
                emergency.latitude = lat
                emergency.longitude = lon
            
            emergency.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Log activity
            log_user_activity(
                action='emergency_update',
                entity_type='emergency_request',
                entity_id=emergency.id,
                details=update_data
            )
            
            return emergency
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_emergency_requests(authority_user, status_filter=None, limit=None):
        """
        Get emergency requests for an authority user.
        
        Args:
            authority_user: The authority user
            status_filter: Filter by status ('open', 'assigned', 'completed', 'cancelled')
            limit: Maximum number of requests to return
            
        Returns:
            List of EmergencyRequest objects
        """
        query = EmergencyRequest.query.filter_by(authority_id=authority_user.id)
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        query = query.order_by(EmergencyRequest.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_emergency_by_id(emergency_id, authority_user=None):
        """
        Get emergency request by ID with optional authority check.
        
        Args:
            emergency_id: ID of the emergency
            authority_user: Optional authority user for access control
            
        Returns:
            EmergencyRequest object or None
        """
        query = EmergencyRequest.query.filter_by(id=emergency_id)
        
        if authority_user:
            query = query.filter_by(authority_id=authority_user.id)
        
        return query.first()
    
    @staticmethod
    def escalate_emergency(emergency_id, authority_user):
        """
        Escalate an emergency request (increase priority and expand radius).
        
        Args:
            emergency_id: ID of the emergency to escalate
            authority_user: The authority user requesting escalation
            
        Returns:
            Updated EmergencyRequest object
        """
        try:
            emergency = EmergencyRequest.query.filter_by(
                id=emergency_id,
                authority_id=authority_user.id
            ).first()
            
            if not emergency:
                raise ValueError("Emergency request not found or access denied")
            
            if emergency.status not in ['open', 'assigned']:
                raise ValueError("Can only escalate open or assigned emergencies")
            
            # Escalate the emergency
            emergency.escalate()
            db.session.commit()
            
            # Log escalation
            ActivityLog.log_emergency_escalation(
                user=authority_user,
                emergency=emergency
            )
            
            # Re-initiate volunteer matching with expanded parameters
            EmergencyService.initiate_volunteer_matching(emergency)
            
            return emergency
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def cancel_emergency(emergency_id, authority_user, reason=None):
        """
        Cancel an emergency request.
        
        Args:
            emergency_id: ID of the emergency to cancel
            authority_user: The authority user cancelling the request
            reason: Optional cancellation reason
            
        Returns:
            Updated EmergencyRequest object
        """
        try:
            emergency = EmergencyRequest.query.filter_by(
                id=emergency_id,
                authority_id=authority_user.id
            ).first()
            
            if not emergency:
                raise ValueError("Emergency request not found or access denied")
            
            if emergency.status in ['completed', 'cancelled']:
                raise ValueError("Emergency is already completed or cancelled")
            
            # Cancel all pending assignments
            pending_assignments = Assignment.query.filter_by(
                emergency_id=emergency.id,
                status='requested'
            ).all()
            
            for assignment in pending_assignments:
                assignment.cancel("Emergency cancelled by authority")
            
            # Update emergency status
            emergency.status = 'cancelled'
            emergency.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            # Log activity
            log_user_activity(
                action='emergency_cancellation',
                entity_type='emergency_request',
                entity_id=emergency.id,
                details={'reason': reason}
            )
            
            return emergency
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def complete_emergency(emergency_id, authority_user, completion_notes=None):
        """
        Mark an emergency request as completed.
        
        Args:
            emergency_id: ID of the emergency to complete
            authority_user: The authority user marking completion
            completion_notes: Optional completion notes
            
        Returns:
            Updated EmergencyRequest object
        """
        try:
            emergency = EmergencyRequest.query.filter_by(
                id=emergency_id,
                authority_id=authority_user.id
            ).first()
            
            if not emergency:
                raise ValueError("Emergency request not found or access denied")
            
            if emergency.status == 'completed':
                raise ValueError("Emergency is already completed")
            
            if emergency.status == 'cancelled':
                raise ValueError("Cannot complete a cancelled emergency")
            
            # Complete all active assignments
            active_assignments = Assignment.query.filter_by(
                emergency_id=emergency.id,
                status='accepted'
            ).all()
            
            for assignment in active_assignments:
                assignment.complete("Emergency completed by authority")
            
            # Update emergency status
            emergency.status = 'completed'
            emergency.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            # Log activity
            log_user_activity(
                action='emergency_completion',
                entity_type='emergency_request',
                entity_id=emergency.id,
                details={'completion_notes': completion_notes}
            )
            
            return emergency
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def initiate_volunteer_matching(emergency):
        """
        Initiate volunteer matching for an emergency request.
        
        Args:
            emergency: The EmergencyRequest object
            
        Returns:
            List of created Assignment objects
        """
        try:
            # Find matching volunteers
            volunteer_matches = MatchingService.find_matching_volunteers(
                emergency, limit=emergency.required_volunteers * 2  # Get extra matches
            )
            
            if not volunteer_matches:
                return []
            
            # Create assignments for the best matches
            assignments = []
            volunteers_to_assign = min(len(volunteer_matches), emergency.required_volunteers)
            
            for i in range(volunteers_to_assign):
                match = volunteer_matches[i]
                volunteer = match['volunteer']
                
                # Check if assignment already exists
                existing_assignment = Assignment.query.filter_by(
                    emergency_id=emergency.id,
                    volunteer_id=volunteer.id
                ).first()
                
                if not existing_assignment:
                    assignment = Assignment(
                        emergency_id=emergency.id,
                        volunteer_id=volunteer.id,
                        status='requested'
                    )
                    db.session.add(assignment)
                    assignments.append(assignment)
            
            db.session.commit()
            
            # Send notifications to assigned volunteers
            from app.services.notification_service import NotificationService
            for assignment in assignments:
                NotificationService.notify_volunteer_assignment(assignment)
            
            return assignments
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def assign_volunteer_manually(emergency_id, volunteer_id, authority_user):
        """
        Manually assign a specific volunteer to an emergency.
        
        Args:
            emergency_id: ID of the emergency
            volunteer_id: ID of the volunteer to assign
            authority_user: The authority user making the assignment
            
        Returns:
            Created Assignment object
        """
        try:
            emergency = EmergencyRequest.query.filter_by(
                id=emergency_id,
                authority_id=authority_user.id
            ).first()
            
            if not emergency:
                raise ValueError("Emergency request not found or access denied")
            
            if emergency.status not in ['open', 'assigned']:
                raise ValueError("Can only assign volunteers to open or assigned emergencies")
            
            # Check if volunteer is available and has required skills
            from app.models.volunteer import VolunteerProfile
            volunteer = db.session.get(VolunteerProfile, volunteer_id)
            
            if not volunteer:
                raise ValueError("Volunteer not found")
            
            if not volunteer.is_available:
                raise ValueError("Volunteer is not currently available")
            
            # Check if assignment already exists
            existing_assignment = Assignment.query.filter_by(
                emergency_id=emergency.id,
                volunteer_id=volunteer.id
            ).first()
            
            if existing_assignment:
                raise ValueError("Volunteer is already assigned to this emergency")
            
            # Create assignment
            assignment = Assignment(
                emergency_id=emergency.id,
                volunteer_id=volunteer.id,
                status='requested'
            )
            
            db.session.add(assignment)
            db.session.commit()
            
            # Log activity
            log_user_activity(
                action='manual_volunteer_assignment',
                entity_type='assignment',
                entity_id=assignment.id,
                details={
                    'emergency_id': emergency.id,
                    'volunteer_id': volunteer.id
                }
            )
            
            return assignment
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_emergency_statistics(emergency_id):
        """
        Get comprehensive statistics for an emergency request.
        
        Args:
            emergency_id: ID of the emergency
            
        Returns:
            Dictionary with emergency statistics
        """
        emergency = db.session.get(EmergencyRequest, emergency_id)
        if not emergency:
            return None
        
        # Get assignment statistics
        assignments = Assignment.query.filter_by(emergency_id=emergency.id).all()
        
        assignment_stats = {
            'total_assignments': len(assignments),
            'requested': len([a for a in assignments if a.status == 'requested']),
            'accepted': len([a for a in assignments if a.status == 'accepted']),
            'declined': len([a for a in assignments if a.status == 'declined']),
            'completed': len([a for a in assignments if a.status == 'completed']),
            'cancelled': len([a for a in assignments if a.status == 'cancelled'])
        }
        
        # Get matching statistics
        matching_stats = MatchingService.get_matching_statistics(emergency)
        
        # Calculate response metrics
        response_times = []
        for assignment in assignments:
            if assignment.response_time_minutes:
                response_times.append(assignment.response_time_minutes)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        return {
            'emergency': emergency.to_dict(include_authority=True, include_skills=True),
            'assignments': assignment_stats,
            'matching': matching_stats,
            'response_metrics': {
                'average_response_time_minutes': avg_response_time,
                'total_responses': len(response_times),
                'volunteers_needed': emergency.volunteers_needed,
                'volunteers_assigned': assignment_stats['accepted'],
                'fulfillment_rate': (assignment_stats['accepted'] / emergency.required_volunteers * 100) 
                                  if emergency.required_volunteers > 0 else 0
            },
            'timeline': {
                'created_at': emergency.created_at,
                'updated_at': emergency.updated_at,
                'expires_at': emergency.expires_at,
                'is_expired': emergency.is_expired,
                'escalation_count': emergency.escalation_count
            }
        }
    
    @staticmethod
    def get_system_emergency_overview():
        """
        Get system-wide emergency overview statistics.
        
        Returns:
            Dictionary with system emergency statistics
        """
        # Get counts by status
        status_counts = {}
        for status in ['open', 'assigned', 'completed', 'cancelled']:
            count = EmergencyRequest.query.filter_by(status=status).count()
            status_counts[status] = count
        
        # Get counts by priority
        priority_counts = {}
        for priority in ['low', 'medium', 'high', 'critical']:
            count = EmergencyRequest.query.filter_by(priority_level=priority).count()
            priority_counts[priority] = count
        
        # Get recent activity
        recent_emergencies = EmergencyRequest.query.order_by(
            EmergencyRequest.created_at.desc()
        ).limit(10).all()
        
        # Get escalated emergencies
        escalated_emergencies = EmergencyRequest.query.filter(
            EmergencyRequest.escalation_count > 0
        ).order_by(EmergencyRequest.escalation_count.desc()).limit(5).all()
        
        return {
            'total_emergencies': sum(status_counts.values()),
            'status_breakdown': status_counts,
            'priority_breakdown': priority_counts,
            'active_emergencies': status_counts['open'] + status_counts['assigned'],
            'recent_emergencies': [e.to_dict(include_authority=True) for e in recent_emergencies],
            'escalated_emergencies': [e.to_dict(include_authority=True) for e in escalated_emergencies]
        }
    
    @staticmethod
    def check_emergency_timeouts():
        """
        Check for emergency requests that have timed out and need escalation.
        
        This method should be called periodically (e.g., via a background task).
        
        Returns:
            List of escalated emergency IDs
        """
        try:
            # Find emergencies that have expired and need escalation
            expired_emergencies = EmergencyRequest.query.filter(
                and_(
                    EmergencyRequest.status.in_(['open', 'assigned']),
                    EmergencyRequest.expires_at < datetime.now(timezone.utc),
                    EmergencyRequest.escalation_count < 3  # Limit escalations
                )
            ).all()
            
            escalated_ids = []
            
            for emergency in expired_emergencies:
                try:
                    # Auto-escalate the emergency
                    emergency.escalate()
                    
                    # Log automatic escalation
                    ActivityLog.log_action(
                        user_id=None,  # System action
                        action='automatic_escalation',
                        entity_type='emergency_request',
                        entity_id=emergency.id,
                        details={
                            'reason': 'timeout',
                            'escalation_count': emergency.escalation_count
                        }
                    )
                    
                    # Re-initiate volunteer matching
                    EmergencyService.initiate_volunteer_matching(emergency)
                    
                    escalated_ids.append(emergency.id)
                    
                except Exception as e:
                    # Log error but continue with other emergencies
                    print(f"Error escalating emergency {emergency.id}: {str(e)}")
                    continue
            
            db.session.commit()
            return escalated_ids
            
        except Exception as e:
            db.session.rollback()
            raise e