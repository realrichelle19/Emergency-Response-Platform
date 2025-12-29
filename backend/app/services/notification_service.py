"""
Notification service for the Emergency Response Platform.

This module provides notification delivery for emergency matches,
assignment updates, and activity history tracking.
"""

from typing import List, Dict, Optional
from flask import current_app
from app import db
from app.models import User, Assignment, EmergencyRequest, ActivityLog
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

class NotificationService:
    """Service class for notification management."""
    
    @staticmethod
    def notify_volunteer_assignment(assignment):
        """
        Notify a volunteer about a new assignment.
        
        Args:
            assignment: The Assignment object
            
        Returns:
            Dictionary with notification details
        """
        try:
            volunteer = assignment.volunteer_profile
            emergency = assignment.emergency_request
            
            # Create notification data
            notification_data = {
                'type': 'assignment_request',
                'assignment_id': assignment.id,
                'emergency_id': emergency.id,
                'volunteer_id': volunteer.id,
                'title': f'New Emergency Assignment: {emergency.title}',
                'message': f'You have been matched for an emergency in {emergency.address or "your area"}. Priority: {emergency.priority_level.title()}',
                'priority': emergency.priority_level,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'expires_at': emergency.expires_at.isoformat() if emergency.expires_at else None,
                'emergency_details': {
                    'title': emergency.title,
                    'description': emergency.description,
                    'priority_level': emergency.priority_level,
                    'location': {
                        'latitude': float(emergency.latitude),
                        'longitude': float(emergency.longitude),
                        'address': emergency.address
                    },
                    'required_volunteers': emergency.required_volunteers,
                    'distance_km': volunteer.get_distance_from(
                        float(emergency.latitude), 
                        float(emergency.longitude)
                    ) if volunteer.latitude and volunteer.longitude else None
                }
            }
            
            # Log notification
            ActivityLog.log_action(
                user_id=volunteer.user_id,
                action='notification_sent',
                entity_type='assignment',
                entity_id=assignment.id,
                details=notification_data
            )
            
            # In a real system, this would send email/SMS/push notification
            # For now, we'll store it as an activity log entry
            return notification_data
            
        except Exception as e:
            print(f"Error sending assignment notification: {str(e)}")
            return None
    
    @staticmethod
    def notify_assignment_response(assignment, response_type):
        """
        Notify relevant parties about assignment response.
        
        Args:
            assignment: The Assignment object
            response_type: 'accepted' or 'declined'
            
        Returns:
            List of notification dictionaries
        """
        try:
            notifications = []
            volunteer = assignment.volunteer_profile
            emergency = assignment.emergency_request
            authority = emergency.authority
            
            # Notify authority about volunteer response
            authority_notification = {
                'type': f'assignment_{response_type}',
                'assignment_id': assignment.id,
                'emergency_id': emergency.id,
                'volunteer_id': volunteer.id,
                'authority_id': authority.id,
                'title': f'Volunteer {response_type.title()} Assignment',
                'message': f'{volunteer.user.full_name} has {response_type} the assignment for "{emergency.title}"',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'volunteer_details': {
                    'name': volunteer.user.full_name,
                    'email': volunteer.user.email,
                    'phone': volunteer.user.phone,
                    'skills': [vs.skill.name for vs in volunteer.verified_skills]
                }
            }
            
            # Log authority notification
            ActivityLog.log_action(
                user_id=authority.id,
                action='notification_sent',
                entity_type='assignment',
                entity_id=assignment.id,
                details=authority_notification
            )
            
            notifications.append(authority_notification)
            
            # If declined, notify about replacement search
            if response_type == 'declined':
                replacement_notification = {
                    'type': 'replacement_search',
                    'emergency_id': emergency.id,
                    'authority_id': authority.id,
                    'title': 'Searching for Replacement Volunteer',
                    'message': f'Looking for alternative volunteers for "{emergency.title}"',
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                notifications.append(replacement_notification)
            
            return notifications
            
        except Exception as e:
            print(f"Error sending response notification: {str(e)}")
            return []
    
    @staticmethod
    def notify_assignment_completion(assignment):
        """
        Notify authority about assignment completion.
        
        Args:
            assignment: The completed Assignment object
            
        Returns:
            Dictionary with notification details
        """
        try:
            volunteer = assignment.volunteer_profile
            emergency = assignment.emergency_request
            authority = emergency.authority
            
            notification_data = {
                'type': 'assignment_completed',
                'assignment_id': assignment.id,
                'emergency_id': emergency.id,
                'volunteer_id': volunteer.id,
                'authority_id': authority.id,
                'title': 'Assignment Completed',
                'message': f'{volunteer.user.full_name} has completed the assignment for "{emergency.title}"',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'completion_details': {
                    'volunteer_name': volunteer.user.full_name,
                    'completion_time_minutes': assignment.completion_time_minutes,
                    'total_time_minutes': assignment.total_time_minutes,
                    'notes': assignment.notes
                }
            }
            
            # Log notification
            ActivityLog.log_action(
                user_id=authority.id,
                action='notification_sent',
                entity_type='assignment',
                entity_id=assignment.id,
                details=notification_data
            )
            
            return notification_data
            
        except Exception as e:
            print(f"Error sending completion notification: {str(e)}")
            return None
    
    @staticmethod
    def notify_emergency_escalation(emergency):
        """
        Notify relevant parties about emergency escalation.
        
        Args:
            emergency: The escalated EmergencyRequest object
            
        Returns:
            List of notification dictionaries
        """
        try:
            notifications = []
            authority = emergency.authority
            
            # Notify authority about escalation
            authority_notification = {
                'type': 'emergency_escalated',
                'emergency_id': emergency.id,
                'authority_id': authority.id,
                'title': 'Emergency Escalated',
                'message': f'Emergency "{emergency.title}" has been escalated to {emergency.priority_level} priority',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'escalation_details': {
                    'new_priority': emergency.priority_level,
                    'escalation_count': emergency.escalation_count,
                    'new_search_radius': emergency.search_radius_km,
                    'expires_at': emergency.expires_at.isoformat() if emergency.expires_at else None
                }
            }
            
            # Log authority notification
            ActivityLog.log_action(
                user_id=authority.id,
                action='notification_sent',
                entity_type='emergency_request',
                entity_id=emergency.id,
                details=authority_notification
            )
            
            notifications.append(authority_notification)
            
            # Notify volunteers with pending assignments about urgency increase
            pending_assignments = Assignment.query.filter_by(
                emergency_id=emergency.id,
                status='requested'
            ).all()
            
            for assignment in pending_assignments:
                volunteer = assignment.volunteer_profile
                volunteer_notification = {
                    'type': 'emergency_escalated',
                    'assignment_id': assignment.id,
                    'emergency_id': emergency.id,
                    'volunteer_id': volunteer.id,
                    'title': 'Emergency Priority Increased',
                    'message': f'The emergency "{emergency.title}" has been escalated to {emergency.priority_level} priority. Your response is urgently needed.',
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'priority': emergency.priority_level
                }
                
                # Log volunteer notification
                ActivityLog.log_action(
                    user_id=volunteer.user_id,
                    action='notification_sent',
                    entity_type='assignment',
                    entity_id=assignment.id,
                    details=volunteer_notification
                )
                
                notifications.append(volunteer_notification)
            
            return notifications
            
        except Exception as e:
            print(f"Error sending escalation notifications: {str(e)}")
            return []
    
    @staticmethod
    def get_volunteer_notifications(volunteer_user, limit=50, unread_only=False):
        """
        Get notifications for a volunteer.
        
        Args:
            volunteer_user: The volunteer user
            limit: Maximum number of notifications to return
            unread_only: If True, only return unread notifications
            
        Returns:
            List of notification dictionaries
        """
        try:
            # Get activity logs that represent notifications
            query = ActivityLog.query.filter(
                and_(
                    ActivityLog.user_id == volunteer_user.id,
                    ActivityLog.action == 'notification_sent'
                )
            ).order_by(ActivityLog.created_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            activity_logs = query.all()
            
            notifications = []
            for log in activity_logs:
                notification = log.details.copy() if log.details else {}
                notification['id'] = log.id
                notification['read'] = False  # In a real system, track read status
                notifications.append(notification)
            
            return notifications
            
        except Exception as e:
            print(f"Error getting volunteer notifications: {str(e)}")
            return []
    
    @staticmethod
    def get_authority_notifications(authority_user, limit=50):
        """
        Get notifications for an authority user.
        
        Args:
            authority_user: The authority user
            limit: Maximum number of notifications to return
            
        Returns:
            List of notification dictionaries
        """
        try:
            # Get activity logs that represent notifications
            query = ActivityLog.query.filter(
                and_(
                    ActivityLog.user_id == authority_user.id,
                    ActivityLog.action == 'notification_sent'
                )
            ).order_by(ActivityLog.created_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            activity_logs = query.all()
            
            notifications = []
            for log in activity_logs:
                notification = log.details.copy() if log.details else {}
                notification['id'] = log.id
                notification['read'] = False  # In a real system, track read status
                notifications.append(notification)
            
            return notifications
            
        except Exception as e:
            print(f"Error getting authority notifications: {str(e)}")
            return []
    
    @staticmethod
    def get_notification_statistics(user):
        """
        Get notification statistics for a user.
        
        Args:
            user: The user
            
        Returns:
            Dictionary with notification statistics
        """
        try:
            # Get all notifications for user
            notifications = ActivityLog.query.filter(
                and_(
                    ActivityLog.user_id == user.id,
                    ActivityLog.action == 'notification_sent'
                )
            ).all()
            
            # Count by type
            type_counts = {}
            for notification in notifications:
                if notification.details and 'type' in notification.details:
                    notification_type = notification.details['type']
                    type_counts[notification_type] = type_counts.get(notification_type, 0) + 1
            
            # Get recent notifications
            recent_notifications = notifications[:10]
            
            return {
                'total_notifications': len(notifications),
                'type_breakdown': type_counts,
                'unread_count': len(notifications),  # In a real system, track read status
                'recent_notifications': [
                    {
                        'id': n.id,
                        'type': n.details.get('type') if n.details else 'unknown',
                        'title': n.details.get('title') if n.details else 'Notification',
                        'created_at': n.created_at.isoformat() if n.created_at else None
                    }
                    for n in recent_notifications
                ]
            }
            
        except Exception as e:
            print(f"Error getting notification statistics: {str(e)}")
            return {
                'total_notifications': 0,
                'type_breakdown': {},
                'unread_count': 0,
                'recent_notifications': []
            }
    
    @staticmethod
    def send_batch_notifications(emergency_id, notification_type, message):
        """
        Send batch notifications for an emergency.
        
        Args:
            emergency_id: ID of the emergency
            notification_type: Type of notification
            message: Notification message
            
        Returns:
            Number of notifications sent
        """
        try:
            emergency = db.session.get(EmergencyRequest, emergency_id)
            if not emergency:
                return 0
            
            # Get all volunteers with assignments for this emergency
            assignments = Assignment.query.filter_by(emergency_id=emergency_id).all()
            
            notifications_sent = 0
            
            for assignment in assignments:
                volunteer = assignment.volunteer_profile
                
                notification_data = {
                    'type': notification_type,
                    'assignment_id': assignment.id,
                    'emergency_id': emergency.id,
                    'volunteer_id': volunteer.id,
                    'title': f'Emergency Update: {emergency.title}',
                    'message': message,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'priority': emergency.priority_level
                }
                
                # Log notification
                ActivityLog.log_action(
                    user_id=volunteer.user_id,
                    action='notification_sent',
                    entity_type='assignment',
                    entity_id=assignment.id,
                    details=notification_data
                )
                
                notifications_sent += 1
            
            return notifications_sent
            
        except Exception as e:
            print(f"Error sending batch notifications: {str(e)}")
            return 0
    
    @staticmethod
    def check_notification_delivery():
        """
        Check notification delivery performance and identify issues.
        
        Returns:
            Dictionary with delivery statistics
        """
        try:
            # Get recent notifications
            recent_notifications = ActivityLog.query.filter(
                and_(
                    ActivityLog.action == 'notification_sent',
                    ActivityLog.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
                )
            ).all()
            
            # Analyze delivery times for assignment notifications
            assignment_notifications = [
                n for n in recent_notifications 
                if n.details and n.details.get('type') == 'assignment_request'
            ]
            
            delivery_times = []
            for notification in assignment_notifications:
                if notification.details and 'assignment_id' in notification.details:
                    assignment = db.session.get(Assignment, notification.details['assignment_id'])
                    if assignment:
                        # Calculate time from assignment creation to notification
                        time_diff = notification.created_at - assignment.assigned_at
                        delivery_times.append(time_diff.total_seconds())
            
            avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
            
            # Check for overdue notifications (assignments without notifications)
            overdue_assignments = Assignment.query.filter(
                and_(
                    Assignment.status == 'requested',
                    Assignment.assigned_at < datetime.now(timezone.utc) - timedelta(minutes=5)
                )
            ).all()
            
            # Filter out assignments that have notifications
            notified_assignment_ids = {
                n.details.get('assignment_id') for n in assignment_notifications 
                if n.details and 'assignment_id' in n.details
            }
            
            truly_overdue = [
                a for a in overdue_assignments 
                if a.id not in notified_assignment_ids
            ]
            
            return {
                'total_notifications_24h': len(recent_notifications),
                'assignment_notifications_24h': len(assignment_notifications),
                'average_delivery_time_seconds': round(avg_delivery_time, 2),
                'overdue_notifications': len(truly_overdue),
                'delivery_performance': {
                    'excellent': len([t for t in delivery_times if t <= 60]),  # <= 1 minute
                    'good': len([t for t in delivery_times if 60 < t <= 300]),  # 1-5 minutes
                    'poor': len([t for t in delivery_times if t > 300])  # > 5 minutes
                }
            }
            
        except Exception as e:
            print(f"Error checking notification delivery: {str(e)}")
            return {
                'total_notifications_24h': 0,
                'assignment_notifications_24h': 0,
                'average_delivery_time_seconds': 0,
                'overdue_notifications': 0,
                'delivery_performance': {'excellent': 0, 'good': 0, 'poor': 0}
            }