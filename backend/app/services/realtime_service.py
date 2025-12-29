"""
Real-time update service for the Emergency Response Platform.

This module provides polling-based real-time updates for emergency status,
assignment changes, and notification delivery within timing requirements.
"""

from typing import List, Dict, Optional, Any
from flask import current_app
from app import db
from app.models import User, VolunteerProfile, EmergencyRequest, Assignment, ActivityLog
from datetime import datetime, timedelta, timezone
from sqlalchemy import and_, or_, func

class RealtimeService:
    """Service class for real-time updates and polling."""
    
    @staticmethod
    def get_volunteer_updates(volunteer_user, last_update_time=None):
        """
        Get real-time updates for a volunteer user.
        
        Args:
            volunteer_user: The volunteer user
            last_update_time: Timestamp of last update (for incremental updates)
            
        Returns:
            Dictionary with volunteer updates
        """
        try:
            if not last_update_time:
                last_update_time = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            updates = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'volunteer_id': volunteer_user.volunteer_profile.id if volunteer_user.volunteer_profile else None,
                'new_assignments': [],
                'assignment_updates': [],
                'notifications': [],
                'profile_changes': {},
                'system_messages': []
            }
            
            if not volunteer_user.volunteer_profile:
                return updates
            
            volunteer_id = volunteer_user.volunteer_profile.id
            
            # Get new assignments since last update
            new_assignments = Assignment.query.filter(
                and_(
                    Assignment.volunteer_id == volunteer_id,
                    Assignment.status == 'requested',
                    Assignment.assigned_at > last_update_time
                )
            ).all()
            
            updates['new_assignments'] = [
                {
                    'id': assignment.id,
                    'emergency_id': assignment.emergency_id,
                    'emergency_title': assignment.emergency_request.title,
                    'emergency_priority': assignment.emergency_request.priority_level,
                    'emergency_location': assignment.emergency_request.address,
                    'assigned_at': assignment.assigned_at.isoformat(),
                    'expires_at': assignment.emergency_request.expires_at.isoformat() if assignment.emergency_request.expires_at else None
                }
                for assignment in new_assignments
            ]
            
            # Get assignment status updates
            updated_assignments = Assignment.query.filter(
                and_(
                    Assignment.volunteer_id == volunteer_id,
                    Assignment.updated_at > last_update_time
                )
            ).all()
            
            updates['assignment_updates'] = [
                {
                    'id': assignment.id,
                    'status': assignment.status,
                    'emergency_title': assignment.emergency_request.title,
                    'updated_at': assignment.updated_at.isoformat() if assignment.updated_at else assignment.assigned_at.isoformat()
                }
                for assignment in updated_assignments
            ]
            
            # Get new notifications
            new_notifications = ActivityLog.query.filter(
                and_(
                    ActivityLog.user_id == volunteer_user.id,
                    ActivityLog.action == 'notification_sent',
                    ActivityLog.created_at > last_update_time
                )
            ).order_by(ActivityLog.created_at.desc()).limit(10).all()
            
            updates['notifications'] = [
                {
                    'id': log.id,
                    'type': log.details.get('type') if log.details else 'notification',
                    'title': log.details.get('title') if log.details else 'Notification',
                    'message': log.details.get('message') if log.details else '',
                    'created_at': log.created_at.isoformat()
                }
                for log in new_notifications
            ]
            
            # Check for profile changes (availability status, etc.)
            profile_logs = ActivityLog.query.filter(
                and_(
                    ActivityLog.user_id == volunteer_user.id,
                    ActivityLog.entity_type == 'volunteer_profile',
                    ActivityLog.created_at > last_update_time
                )
            ).all()
            
            if profile_logs:
                updates['profile_changes'] = {
                    'availability_status': volunteer_user.volunteer_profile.availability_status,
                    'updated_at': volunteer_user.volunteer_profile.updated_at.isoformat()
                }
            
            # Get system messages (emergency escalations, etc.)
            system_messages = ActivityLog.query.filter(
                and_(
                    ActivityLog.user_id == volunteer_user.id,
                    ActivityLog.action.in_(['emergency_escalated', 'assignment_cancelled']),
                    ActivityLog.created_at > last_update_time
                )
            ).all()
            
            updates['system_messages'] = [
                {
                    'type': log.action,
                    'message': RealtimeService._format_system_message(log),
                    'created_at': log.created_at.isoformat()
                }
                for log in system_messages
            ]
            
            return updates
            
        except Exception as e:
            current_app.logger.error(f"Error getting volunteer updates: {str(e)}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': 'Failed to get updates',
                'new_assignments': [],
                'assignment_updates': [],
                'notifications': [],
                'profile_changes': {},
                'system_messages': []
            }
    
    @staticmethod
    def get_authority_updates(authority_user, last_update_time=None):
        """
        Get real-time updates for an authority user.
        
        Args:
            authority_user: The authority user
            last_update_time: Timestamp of last update
            
        Returns:
            Dictionary with authority updates
        """
        try:
            if not last_update_time:
                last_update_time = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            updates = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'authority_id': authority_user.id,
                'emergency_updates': [],
                'assignment_responses': [],
                'notifications': [],
                'system_alerts': []
            }
            
            # Get emergency status updates
            updated_emergencies = EmergencyRequest.query.filter(
                and_(
                    EmergencyRequest.authority_id == authority_user.id,
                    EmergencyRequest.updated_at > last_update_time
                )
            ).all()
            
            updates['emergency_updates'] = [
                {
                    'id': emergency.id,
                    'title': emergency.title,
                    'status': emergency.status,
                    'priority_level': emergency.priority_level,
                    'escalation_count': emergency.escalation_count,
                    'volunteers_needed': emergency.volunteers_needed,
                    'updated_at': emergency.updated_at.isoformat()
                }
                for emergency in updated_emergencies
            ]
            
            # Get assignment responses for authority's emergencies
            authority_emergency_ids = [e.id for e in EmergencyRequest.query.filter_by(
                authority_id=authority_user.id
            ).all()]
            
            if authority_emergency_ids:
                assignment_responses = Assignment.query.filter(
                    and_(
                        Assignment.emergency_id.in_(authority_emergency_ids),
                        Assignment.responded_at > last_update_time
                    )
                ).all()
                
                updates['assignment_responses'] = [
                    {
                        'id': assignment.id,
                        'emergency_id': assignment.emergency_id,
                        'emergency_title': assignment.emergency_request.title,
                        'volunteer_name': assignment.volunteer_profile.user.full_name,
                        'status': assignment.status,
                        'responded_at': assignment.responded_at.isoformat()
                    }
                    for assignment in assignment_responses
                ]
            
            # Get new notifications
            new_notifications = ActivityLog.query.filter(
                and_(
                    ActivityLog.user_id == authority_user.id,
                    ActivityLog.action == 'notification_sent',
                    ActivityLog.created_at > last_update_time
                )
            ).order_by(ActivityLog.created_at.desc()).limit(10).all()
            
            updates['notifications'] = [
                {
                    'id': log.id,
                    'type': log.details.get('type') if log.details else 'notification',
                    'title': log.details.get('title') if log.details else 'Notification',
                    'message': log.details.get('message') if log.details else '',
                    'created_at': log.created_at.isoformat()
                }
                for log in new_notifications
            ]
            
            # Get system alerts (escalations, timeouts, etc.)
            system_alerts = ActivityLog.query.filter(
                and_(
                    ActivityLog.user_id == authority_user.id,
                    ActivityLog.action.in_(['emergency_escalated', 'automatic_escalation']),
                    ActivityLog.created_at > last_update_time
                )
            ).all()
            
            updates['system_alerts'] = [
                {
                    'type': log.action,
                    'message': RealtimeService._format_system_message(log),
                    'severity': 'warning' if 'escalation' in log.action else 'info',
                    'created_at': log.created_at.isoformat()
                }
                for log in system_alerts
            ]
            
            return updates
            
        except Exception as e:
            current_app.logger.error(f"Error getting authority updates: {str(e)}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': 'Failed to get updates',
                'emergency_updates': [],
                'assignment_responses': [],
                'notifications': [],
                'system_alerts': []
            }
    
    @staticmethod
    def get_admin_updates(admin_user, last_update_time=None):
        """
        Get real-time updates for an admin user.
        
        Args:
            admin_user: The admin user
            last_update_time: Timestamp of last update
            
        Returns:
            Dictionary with admin updates
        """
        try:
            if not last_update_time:
                last_update_time = datetime.now(timezone.utc) - timedelta(minutes=30)
            
            updates = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'admin_id': admin_user.id,
                'pending_verifications': 0,
                'new_users': 0,
                'system_alerts': [],
                'activity_summary': {}
            }
            
            # Get pending skill verifications count
            from app.models.volunteer import VolunteerSkill
            pending_count = VolunteerSkill.query.filter_by(verification_status='pending').count()
            updates['pending_verifications'] = pending_count
            
            # Get new user registrations
            new_users_count = User.query.filter(
                User.created_at > last_update_time
            ).count()
            updates['new_users'] = new_users_count
            
            # Get system alerts (high priority emergencies, overdue assignments, etc.)
            critical_emergencies = EmergencyRequest.query.filter(
                and_(
                    EmergencyRequest.priority_level == 'critical',
                    EmergencyRequest.status.in_(['open', 'assigned']),
                    EmergencyRequest.created_at > last_update_time
                )
            ).count()
            
            if critical_emergencies > 0:
                updates['system_alerts'].append({
                    'type': 'critical_emergencies',
                    'message': f'{critical_emergencies} new critical emergencies require attention',
                    'severity': 'danger',
                    'count': critical_emergencies
                })
            
            # Get activity summary
            recent_activity = ActivityLog.query.filter(
                ActivityLog.created_at > last_update_time
            ).count()
            
            updates['activity_summary'] = {
                'total_actions': recent_activity,
                'period_minutes': int((datetime.now(timezone.utc) - last_update_time).total_seconds() / 60)
            }
            
            return updates
            
        except Exception as e:
            current_app.logger.error(f"Error getting admin updates: {str(e)}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': 'Failed to get updates',
                'pending_verifications': 0,
                'new_users': 0,
                'system_alerts': [],
                'activity_summary': {}
            }
    
    @staticmethod
    def check_notification_delivery_timing():
        """
        Check if notifications are being delivered within the 1-minute requirement.
        
        Returns:
            Dictionary with delivery timing analysis
        """
        try:
            # Get recent assignment notifications
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            
            assignment_notifications = ActivityLog.query.filter(
                and_(
                    ActivityLog.action == 'notification_sent',
                    ActivityLog.entity_type == 'assignment',
                    ActivityLog.created_at > one_hour_ago
                )
            ).all()
            
            delivery_times = []
            overdue_notifications = []
            
            for notification in assignment_notifications:
                if notification.details and 'assignment_id' in notification.details:
                    assignment_id = notification.details['assignment_id']
                    assignment = db.session.get(Assignment, assignment_id)
                    
                    if assignment:
                        # Calculate delivery time from assignment creation to notification
                        delivery_time = (notification.created_at - assignment.assigned_at).total_seconds()
                        delivery_times.append(delivery_time)
                        
                        # Check if delivery was within 1 minute (60 seconds)
                        if delivery_time > 60:
                            overdue_notifications.append({
                                'assignment_id': assignment_id,
                                'delivery_time_seconds': delivery_time,
                                'volunteer_id': assignment.volunteer_id,
                                'emergency_id': assignment.emergency_id
                            })
            
            avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
            
            # Performance categories
            excellent = len([t for t in delivery_times if t <= 30])  # <= 30 seconds
            good = len([t for t in delivery_times if 30 < t <= 60])  # 30-60 seconds
            poor = len([t for t in delivery_times if t > 60])  # > 60 seconds
            
            return {
                'total_notifications': len(delivery_times),
                'average_delivery_time_seconds': round(avg_delivery_time, 2),
                'overdue_count': len(overdue_notifications),
                'performance_breakdown': {
                    'excellent': excellent,
                    'good': good,
                    'poor': poor
                },
                'compliance_rate': round((excellent + good) / len(delivery_times) * 100, 2) if delivery_times else 100,
                'overdue_notifications': overdue_notifications[:10]  # Limit to 10 for response size
            }
            
        except Exception as e:
            current_app.logger.error(f"Error checking notification delivery timing: {str(e)}")
            return {
                'total_notifications': 0,
                'average_delivery_time_seconds': 0,
                'overdue_count': 0,
                'performance_breakdown': {'excellent': 0, 'good': 0, 'poor': 0},
                'compliance_rate': 100,
                'overdue_notifications': []
            }
    
    @staticmethod
    def trigger_emergency_escalations():
        """
        Check for and trigger emergency escalations based on timeouts.
        
        This should be called periodically (e.g., every minute) by a background process.
        
        Returns:
            List of escalated emergency IDs
        """
        try:
            from app.services.emergency_service import EmergencyService
            
            # Find emergencies that need escalation
            escalation_timeout = current_app.config.get('ESCALATION_TIMEOUT_MINUTES', 30)
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=escalation_timeout)
            
            # Get emergencies that are overdue for escalation
            overdue_emergencies = EmergencyRequest.query.filter(
                and_(
                    EmergencyRequest.status.in_(['open', 'assigned']),
                    EmergencyRequest.created_at < cutoff_time,
                    EmergencyRequest.escalation_count < 3,  # Limit escalations
                    or_(
                        EmergencyRequest.expires_at.is_(None),
                        EmergencyRequest.expires_at < datetime.now(timezone.utc)
                    )
                )
            ).all()
            
            escalated_ids = []
            
            for emergency in overdue_emergencies:
                try:
                    # Check if emergency still needs volunteers
                    active_assignments = Assignment.query.filter_by(
                        emergency_id=emergency.id,
                        status='accepted'
                    ).count()
                    
                    if active_assignments < emergency.required_volunteers:
                        # Escalate the emergency
                        emergency.escalate()
                        
                        # Log automatic escalation
                        ActivityLog.log_action(
                            user_id=None,  # System action
                            action='automatic_escalation',
                            entity_type='emergency_request',
                            entity_id=emergency.id,
                            details={
                                'reason': 'timeout',
                                'escalation_count': emergency.escalation_count,
                                'new_priority': emergency.priority_level,
                                'new_radius': emergency.search_radius_km
                            }
                        )
                        
                        # Re-initiate volunteer matching
                        EmergencyService.initiate_volunteer_matching(emergency)
                        
                        escalated_ids.append(emergency.id)
                        
                except Exception as e:
                    current_app.logger.error(f"Error escalating emergency {emergency.id}: {str(e)}")
                    continue
            
            if escalated_ids:
                db.session.commit()
            
            return escalated_ids
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error triggering emergency escalations: {str(e)}")
            return []
    
    @staticmethod
    def get_system_health_status():
        """
        Get overall system health status for monitoring.
        
        Returns:
            Dictionary with system health metrics
        """
        try:
            now = datetime.now(timezone.utc)
            one_hour_ago = now - timedelta(hours=1)
            
            # Check notification delivery performance
            notification_health = RealtimeService.check_notification_delivery_timing()
            
            # Check for stuck assignments (requested for too long)
            stuck_assignments = Assignment.query.filter(
                and_(
                    Assignment.status == 'requested',
                    Assignment.assigned_at < now - timedelta(hours=2)
                )
            ).count()
            
            # Check for overdue emergencies
            overdue_emergencies = EmergencyRequest.query.filter(
                and_(
                    EmergencyRequest.status == 'open',
                    EmergencyRequest.created_at < now - timedelta(hours=1)
                )
            ).count()
            
            # Check recent activity level
            recent_activity = ActivityLog.query.filter(
                ActivityLog.created_at > one_hour_ago
            ).count()
            
            # Calculate health score
            health_score = 100
            
            if notification_health['compliance_rate'] < 90:
                health_score -= 20
            if stuck_assignments > 5:
                health_score -= 15
            if overdue_emergencies > 3:
                health_score -= 25
            
            health_status = 'excellent' if health_score >= 90 else \
                           'good' if health_score >= 70 else \
                           'fair' if health_score >= 50 else 'poor'
            
            return {
                'timestamp': now.isoformat(),
                'health_score': max(0, health_score),
                'health_status': health_status,
                'metrics': {
                    'notification_compliance_rate': notification_health['compliance_rate'],
                    'stuck_assignments': stuck_assignments,
                    'overdue_emergencies': overdue_emergencies,
                    'recent_activity_count': recent_activity
                },
                'alerts': [
                    'Notification delivery below 90% compliance' if notification_health['compliance_rate'] < 90 else None,
                    f'{stuck_assignments} assignments stuck in requested status' if stuck_assignments > 5 else None,
                    f'{overdue_emergencies} emergencies overdue for response' if overdue_emergencies > 3 else None
                ]
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting system health status: {str(e)}")
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'health_score': 0,
                'health_status': 'error',
                'metrics': {},
                'alerts': [f'System health check failed: {str(e)}']
            }
    
    @staticmethod
    def _format_system_message(activity_log):
        """
        Format system message from activity log.
        
        Args:
            activity_log: ActivityLog object
            
        Returns:
            Formatted message string
        """
        if activity_log.action == 'emergency_escalated':
            if activity_log.details:
                priority = activity_log.details.get('new_priority', 'unknown')
                return f"Emergency escalated to {priority} priority"
            return "Emergency has been escalated"
        
        elif activity_log.action == 'assignment_cancelled':
            return "Your assignment has been cancelled"
        
        elif activity_log.action == 'automatic_escalation':
            if activity_log.details:
                priority = activity_log.details.get('new_priority', 'unknown')
                return f"Emergency automatically escalated to {priority} priority due to timeout"
            return "Emergency automatically escalated due to timeout"
        
        return f"System message: {activity_log.action.replace('_', ' ').title()}"