"""
Assignment management service for the Emergency Response Platform.

This module provides comprehensive assignment management including
volunteer request acceptance/decline, state tracking, and notification handling.
"""

from typing import List, Dict, Optional
from flask import current_app
from app import db
from app.models import Assignment, EmergencyRequest, VolunteerProfile, ActivityLog
from app.auth.utils import log_user_activity
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

class AssignmentService:
    """Service class for assignment management."""
    
    @staticmethod
    def accept_assignment(assignment_id, volunteer_user, notes=None):
        """
        Accept an assignment request.
        
        Args:
            assignment_id: ID of the assignment to accept
            volunteer_user: The volunteer user accepting the assignment
            notes: Optional notes from the volunteer
            
        Returns:
            Updated Assignment object
        """
        try:
            # Get assignment and verify it belongs to the volunteer
            assignment = Assignment.query.filter_by(
                id=assignment_id,
                volunteer_id=volunteer_user.volunteer_profile.id
            ).first()
            
            if not assignment:
                raise ValueError("Assignment not found or access denied")
            
            if assignment.status != 'requested':
                raise ValueError("Can only accept requested assignments")
            
            # Check if volunteer is still available
            if not volunteer_user.volunteer_profile.is_available:
                raise ValueError("Volunteer is not currently available")
            
            # Accept the assignment
            assignment.accept(notes)
            
            # Update volunteer availability to busy
            volunteer_user.volunteer_profile.availability_status = 'busy'
            
            db.session.commit()
            
            # Log activity
            ActivityLog.log_assignment_acceptance(
                user=volunteer_user,
                assignment=assignment
            )
            
            # Send notification to authority
            from app.services.notification_service import NotificationService
            NotificationService.notify_assignment_response(assignment, 'accepted')
            
            return assignment
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def decline_assignment(assignment_id, volunteer_user, notes=None):
        """
        Decline an assignment request.
        
        Args:
            assignment_id: ID of the assignment to decline
            volunteer_user: The volunteer user declining the assignment
            notes: Optional notes from the volunteer
            
        Returns:
            Updated Assignment object
        """
        try:
            # Get assignment and verify it belongs to the volunteer
            assignment = Assignment.query.filter_by(
                id=assignment_id,
                volunteer_id=volunteer_user.volunteer_profile.id
            ).first()
            
            if not assignment:
                raise ValueError("Assignment not found or access denied")
            
            if assignment.status != 'requested':
                raise ValueError("Can only decline requested assignments")
            
            # Decline the assignment
            assignment.decline(notes)
            
            db.session.commit()
            
            # Log activity
            ActivityLog.log_assignment_decline(
                user=volunteer_user,
                assignment=assignment
            )
            
            # Send notification to authority
            from app.services.notification_service import NotificationService
            NotificationService.notify_assignment_response(assignment, 'declined')
            
            # Try to find replacement volunteers for the emergency
            AssignmentService._find_replacement_volunteers(assignment.emergency_request)
            
            return assignment
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def complete_assignment(assignment_id, volunteer_user, notes=None):
        """
        Mark an assignment as completed.
        
        Args:
            assignment_id: ID of the assignment to complete
            volunteer_user: The volunteer user completing the assignment
            notes: Optional completion notes
            
        Returns:
            Updated Assignment object
        """
        try:
            # Get assignment and verify it belongs to the volunteer
            assignment = Assignment.query.filter_by(
                id=assignment_id,
                volunteer_id=volunteer_user.volunteer_profile.id
            ).first()
            
            if not assignment:
                raise ValueError("Assignment not found or access denied")
            
            if assignment.status != 'accepted':
                raise ValueError("Can only complete accepted assignments")
            
            # Complete the assignment
            assignment.complete(notes)
            
            # Update volunteer availability back to available
            volunteer_user.volunteer_profile.availability_status = 'available'
            
            db.session.commit()
            
            # Log activity
            ActivityLog.log_assignment_completion(
                user=volunteer_user,
                assignment=assignment
            )
            
            # Send notification to authority
            from app.services.notification_service import NotificationService
            NotificationService.notify_assignment_completion(assignment)
            
            return assignment
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def cancel_assignment(assignment_id, user, notes=None):
        """
        Cancel an assignment (can be done by volunteer or authority).
        
        Args:
            assignment_id: ID of the assignment to cancel
            user: The user cancelling the assignment
            notes: Optional cancellation notes
            
        Returns:
            Updated Assignment object
        """
        try:
            assignment = db.session.get(Assignment, assignment_id)
            
            if not assignment:
                raise ValueError("Assignment not found")
            
            # Check permissions
            can_cancel = False
            if user.role == 'volunteer' and assignment.volunteer_id == user.volunteer_profile.id:
                can_cancel = True
            elif user.role == 'authority' and assignment.emergency_request.authority_id == user.id:
                can_cancel = True
            elif user.role == 'admin':
                can_cancel = True
            
            if not can_cancel:
                raise ValueError("Access denied: cannot cancel this assignment")
            
            if assignment.status in ['completed', 'cancelled']:
                raise ValueError("Cannot cancel completed or already cancelled assignments")
            
            # Check if this was an accepted assignment before cancelling
            was_accepted = assignment.status == 'accepted'
            
            # Cancel the assignment
            assignment.cancel(notes)
            
            # If volunteer was busy with this assignment, make them available again
            if was_accepted and user.role == 'volunteer':
                user.volunteer_profile.availability_status = 'available'
            
            db.session.commit()
            
            # Log activity
            ActivityLog.log_assignment_cancellation(
                user=user,
                assignment=assignment
            )
            
            # Try to find replacement volunteers if this was an accepted assignment
            if assignment.status == 'accepted':
                AssignmentService._find_replacement_volunteers(assignment.emergency_request)
            
            return assignment
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_volunteer_assignments(volunteer_user, status_filter=None, limit=None):
        """
        Get assignments for a volunteer.
        
        Args:
            volunteer_user: The volunteer user
            status_filter: Filter by status ('requested', 'accepted', 'declined', 'completed', 'cancelled')
            limit: Maximum number of assignments to return
            
        Returns:
            List of Assignment objects
        """
        query = Assignment.query.filter_by(volunteer_id=volunteer_user.volunteer_profile.id)
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        query = query.order_by(Assignment.assigned_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_pending_assignments(volunteer_user):
        """
        Get pending assignments for a volunteer.
        
        Args:
            volunteer_user: The volunteer user
            
        Returns:
            List of pending Assignment objects
        """
        return Assignment.query.filter_by(
            volunteer_id=volunteer_user.volunteer_profile.id,
            status='requested'
        ).order_by(Assignment.assigned_at.desc()).all()
    
    @staticmethod
    def get_active_assignments(volunteer_user):
        """
        Get active assignments for a volunteer.
        
        Args:
            volunteer_user: The volunteer user
            
        Returns:
            List of active Assignment objects
        """
        return Assignment.query.filter_by(
            volunteer_id=volunteer_user.volunteer_profile.id,
            status='accepted'
        ).order_by(Assignment.assigned_at.desc()).all()
    
    @staticmethod
    def get_assignment_history(volunteer_user, limit=50):
        """
        Get assignment history for a volunteer.
        
        Args:
            volunteer_user: The volunteer user
            limit: Maximum number of assignments to return
            
        Returns:
            List of Assignment objects
        """
        return Assignment.query.filter_by(
            volunteer_id=volunteer_user.volunteer_profile.id
        ).order_by(Assignment.assigned_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_emergency_assignments(emergency_id, authority_user=None):
        """
        Get all assignments for an emergency.
        
        Args:
            emergency_id: ID of the emergency
            authority_user: Optional authority user for access control
            
        Returns:
            List of Assignment objects
        """
        query = Assignment.query.filter_by(emergency_id=emergency_id)
        
        # If authority user provided, verify they own the emergency
        if authority_user:
            emergency = EmergencyRequest.query.filter_by(
                id=emergency_id,
                authority_id=authority_user.id
            ).first()
            
            if not emergency:
                raise ValueError("Emergency not found or access denied")
        
        return query.order_by(Assignment.assigned_at.desc()).all()
    
    @staticmethod
    def get_assignment_statistics(assignment_id):
        """
        Get statistics for a specific assignment.
        
        Args:
            assignment_id: ID of the assignment
            
        Returns:
            Dictionary with assignment statistics
        """
        assignment = db.session.get(Assignment, assignment_id)
        if not assignment:
            return None
        
        return {
            'assignment': assignment.to_dict(include_emergency=True, include_volunteer=True),
            'timing': {
                'assigned_at': assignment.assigned_at,
                'responded_at': assignment.responded_at,
                'completed_at': assignment.completed_at,
                'response_time_minutes': assignment.response_time_minutes,
                'completion_time_minutes': assignment.completion_time_minutes,
                'total_time_minutes': assignment.total_time_minutes
            },
            'status_history': AssignmentService._get_status_history(assignment)
        }
    
    @staticmethod
    def get_volunteer_statistics(volunteer_user):
        """
        Get comprehensive statistics for a volunteer's assignments.
        
        Args:
            volunteer_user: The volunteer user
            
        Returns:
            Dictionary with volunteer assignment statistics
        """
        assignments = Assignment.query.filter_by(
            volunteer_id=volunteer_user.volunteer_profile.id
        ).all()
        
        # Calculate statistics
        total_assignments = len(assignments)
        status_counts = {}
        for status in ['requested', 'accepted', 'declined', 'completed', 'cancelled']:
            status_counts[status] = len([a for a in assignments if a.status == status])
        
        # Response time statistics
        response_times = [a.response_time_minutes for a in assignments if a.response_time_minutes]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        # Completion time statistics
        completion_times = [a.completion_time_minutes for a in assignments if a.completion_time_minutes]
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else None
        
        # Calculate acceptance rate
        total_responses = status_counts['accepted'] + status_counts['declined']
        acceptance_rate = (status_counts['accepted'] / total_responses * 100) if total_responses > 0 else 0
        
        # Calculate completion rate
        completion_rate = (status_counts['completed'] / status_counts['accepted'] * 100) if status_counts['accepted'] > 0 else 0
        
        return {
            'volunteer': volunteer_user.volunteer_profile.to_dict(include_user=True),
            'assignment_counts': {
                'total': total_assignments,
                **status_counts
            },
            'performance_metrics': {
                'acceptance_rate': round(acceptance_rate, 2),
                'completion_rate': round(completion_rate, 2),
                'average_response_time_minutes': round(avg_response_time, 2) if avg_response_time else None,
                'average_completion_time_minutes': round(avg_completion_time, 2) if avg_completion_time else None
            },
            'recent_assignments': [a.to_dict(include_emergency=True) for a in assignments[:10]]
        }
    
    @staticmethod
    def _find_replacement_volunteers(emergency):
        """
        Find replacement volunteers when an assignment is declined or cancelled.
        
        Args:
            emergency: The EmergencyRequest object
        """
        try:
            # Only find replacements if emergency still needs volunteers
            if emergency.volunteers_needed <= 0:
                return
            
            # Import here to avoid circular imports
            from app.services.emergency_service import EmergencyService
            
            # Re-initiate volunteer matching
            EmergencyService.initiate_volunteer_matching(emergency)
            
        except Exception as e:
            # Log error but don't raise - this is a background operation
            print(f"Error finding replacement volunteers for emergency {emergency.id}: {str(e)}")
    
    @staticmethod
    def _get_status_history(assignment):
        """
        Get status change history for an assignment.
        
        Args:
            assignment: The Assignment object
            
        Returns:
            List of status changes with timestamps
        """
        history = []
        
        # Initial assignment
        history.append({
            'status': 'requested',
            'timestamp': assignment.assigned_at,
            'description': 'Assignment created'
        })
        
        # Response (accept/decline)
        if assignment.responded_at:
            if assignment.status in ['accepted', 'declined']:
                history.append({
                    'status': assignment.status,
                    'timestamp': assignment.responded_at,
                    'description': f'Assignment {assignment.status}'
                })
        
        # Completion
        if assignment.completed_at:
            history.append({
                'status': 'completed',
                'timestamp': assignment.completed_at,
                'description': 'Assignment completed'
            })
        
        return history
    
    @staticmethod
    def check_overdue_assignments():
        """
        Check for assignments that are overdue and need attention.
        
        This method should be called periodically (e.g., via a background task).
        
        Returns:
            Dictionary with overdue assignment information
        """
        try:
            # Get configuration values
            response_timeout_minutes = current_app.config.get('ASSIGNMENT_RESPONSE_TIMEOUT_MINUTES', 60)
            completion_timeout_hours = current_app.config.get('ASSIGNMENT_COMPLETION_TIMEOUT_HOURS', 24)
            
            now = datetime.now(timezone.utc)
            
            # Find overdue requested assignments (no response)
            overdue_requests = Assignment.query.filter(
                and_(
                    Assignment.status == 'requested',
                    Assignment.assigned_at < now - timedelta(minutes=response_timeout_minutes)
                )
            ).all()
            
            # Find overdue accepted assignments (not completed)
            overdue_completions = Assignment.query.filter(
                and_(
                    Assignment.status == 'accepted',
                    Assignment.responded_at < now - timedelta(hours=completion_timeout_hours)
                )
            ).all()
            
            return {
                'overdue_requests': [a.to_dict(include_emergency=True, include_volunteer=True) for a in overdue_requests],
                'overdue_completions': [a.to_dict(include_emergency=True, include_volunteer=True) for a in overdue_completions],
                'total_overdue': len(overdue_requests) + len(overdue_completions)
            }
            
        except Exception as e:
            print(f"Error checking overdue assignments: {str(e)}")
            return {
                'overdue_requests': [],
                'overdue_completions': [],
                'total_overdue': 0,
                'error': str(e)
            }
    
    @staticmethod
    def get_system_assignment_overview():
        """
        Get system-wide assignment overview statistics.
        
        Returns:
            Dictionary with system assignment statistics
        """
        # Get counts by status
        status_counts = {}
        for status in ['requested', 'accepted', 'declined', 'completed', 'cancelled']:
            count = Assignment.query.filter_by(status=status).count()
            status_counts[status] = count
        
        # Get recent assignments
        recent_assignments = Assignment.query.order_by(
            Assignment.assigned_at.desc()
        ).limit(10).all()
        
        # Get overdue information
        overdue_info = AssignmentService.check_overdue_assignments()
        
        # Calculate performance metrics
        total_responses = status_counts['accepted'] + status_counts['declined']
        acceptance_rate = (status_counts['accepted'] / total_responses * 100) if total_responses > 0 else 0
        completion_rate = (status_counts['completed'] / status_counts['accepted'] * 100) if status_counts['accepted'] > 0 else 0
        
        return {
            'total_assignments': sum(status_counts.values()),
            'status_breakdown': status_counts,
            'active_assignments': status_counts['requested'] + status_counts['accepted'],
            'performance_metrics': {
                'acceptance_rate': round(acceptance_rate, 2),
                'completion_rate': round(completion_rate, 2)
            },
            'overdue_assignments': overdue_info['total_overdue'],
            'recent_assignments': [a.to_dict(include_emergency=True, include_volunteer=True) for a in recent_assignments]
        }