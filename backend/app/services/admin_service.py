"""
Admin management service for the Emergency Response Platform.

This module provides comprehensive admin management including
skill verification workflow, user management, and system reporting.
"""

from typing import List, Dict, Optional, Tuple
from flask import current_app
from app import db
from app.models import User, VolunteerProfile, VolunteerSkill, Skill, EmergencyRequest, Assignment, ActivityLog
from app.auth.utils import log_user_activity
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func, desc

class AdminService:
    """Service class for admin management operations."""
    
    @staticmethod
    def get_pending_skill_verifications(limit=None, skill_category=None):
        """
        Get pending skill verification requests.
        
        Args:
            limit: Maximum number of verifications to return
            skill_category: Filter by skill category
            
        Returns:
            List of VolunteerSkill objects pending verification
        """
        query = VolunteerSkill.query.filter_by(verification_status='pending')
        
        if skill_category:
            query = query.join(Skill).filter(Skill.category == skill_category)
        
        query = query.order_by(VolunteerSkill.created_at.asc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def approve_skill_verification(skill_verification_id, admin_user, notes=None):
        """
        Approve a skill verification request.
        
        Args:
            skill_verification_id: ID of the VolunteerSkill to approve
            admin_user: The admin user approving the skill
            notes: Optional approval notes
            
        Returns:
            Updated VolunteerSkill object
        """
        try:
            volunteer_skill = db.session.get(VolunteerSkill, skill_verification_id)
            
            if not volunteer_skill:
                raise ValueError("Skill verification request not found")
            
            if volunteer_skill.verification_status != 'pending':
                raise ValueError("Can only approve pending skill verifications")
            
            # Approve the skill
            volunteer_skill.approve(admin_user, notes)
            
            db.session.commit()
            
            # Log activity
            ActivityLog.log_skill_verification_decision(
                admin_user=admin_user,
                volunteer_skill=volunteer_skill,
                decision='approved',
                notes=notes
            )
            
            # Send notification to volunteer
            from app.services.notification_service import NotificationService
            AdminService._notify_skill_verification_decision(volunteer_skill, 'approved')
            
            return volunteer_skill
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def reject_skill_verification(skill_verification_id, admin_user, notes=None):
        """
        Reject a skill verification request.
        
        Args:
            skill_verification_id: ID of the VolunteerSkill to reject
            admin_user: The admin user rejecting the skill
            notes: Optional rejection notes
            
        Returns:
            Updated VolunteerSkill object
        """
        try:
            volunteer_skill = db.session.get(VolunteerSkill, skill_verification_id)
            
            if not volunteer_skill:
                raise ValueError("Skill verification request not found")
            
            if volunteer_skill.verification_status != 'pending':
                raise ValueError("Can only reject pending skill verifications")
            
            # Reject the skill
            volunteer_skill.reject(admin_user, notes)
            
            db.session.commit()
            
            # Log activity
            ActivityLog.log_skill_verification_decision(
                admin_user=admin_user,
                volunteer_skill=volunteer_skill,
                decision='rejected',
                notes=notes
            )
            
            # Send notification to volunteer
            AdminService._notify_skill_verification_decision(volunteer_skill, 'rejected')
            
            return volunteer_skill
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_skill_verification_statistics():
        """
        Get comprehensive skill verification statistics.
        
        Returns:
            Dictionary with verification statistics
        """
        # Get counts by status
        status_counts = {}
        for status in ['pending', 'verified', 'rejected']:
            count = VolunteerSkill.query.filter_by(verification_status=status).count()
            status_counts[status] = count
        
        # Get counts by skill category
        category_stats = db.session.query(
            Skill.category,
            func.count(VolunteerSkill.id).label('total'),
            func.sum(func.case([(VolunteerSkill.verification_status == 'verified', 1)], else_=0)).label('verified'),
            func.sum(func.case([(VolunteerSkill.verification_status == 'pending', 1)], else_=0)).label('pending'),
            func.sum(func.case([(VolunteerSkill.verification_status == 'rejected', 1)], else_=0)).label('rejected')
        ).join(VolunteerSkill).group_by(Skill.category).all()
        
        category_breakdown = {}
        for stat in category_stats:
            category_breakdown[stat.category] = {
                'total': stat.total,
                'verified': stat.verified,
                'pending': stat.pending,
                'rejected': stat.rejected,
                'verification_rate': round((stat.verified / stat.total * 100) if stat.total > 0 else 0, 2)
            }
        
        # Get recent verification activity
        recent_verifications = VolunteerSkill.query.filter(
            VolunteerSkill.verification_status.in_(['verified', 'rejected'])
        ).order_by(VolunteerSkill.verified_at.desc()).limit(10).all()
        
        return {
            'total_requests': sum(status_counts.values()),
            'status_breakdown': status_counts,
            'category_breakdown': category_breakdown,
            'verification_rate': round(
                (status_counts['verified'] / sum(status_counts.values()) * 100) 
                if sum(status_counts.values()) > 0 else 0, 2
            ),
            'recent_verifications': [
                vs.to_dict(include_skill=True, include_volunteer=True) 
                for vs in recent_verifications
            ]
        }
    
    @staticmethod
    def get_user_management_overview():
        """
        Get user management overview statistics.
        
        Returns:
            Dictionary with user management statistics
        """
        # Get user counts by role
        role_counts = {}
        for role in ['volunteer', 'authority', 'admin']:
            count = User.query.filter_by(role=role, is_active=True).count()
            role_counts[role] = count
        
        # Get inactive user count
        inactive_users = User.query.filter_by(is_active=False).count()
        
        # Get recent user registrations
        recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
        
        # Get volunteer profile completion statistics
        total_volunteers = User.query.filter_by(role='volunteer', is_active=True).count()
        volunteers_with_profiles = VolunteerProfile.query.count()
        volunteers_with_skills = db.session.query(VolunteerProfile.id).join(
            VolunteerSkill
        ).distinct().count()
        
        return {
            'total_users': sum(role_counts.values()),
            'role_breakdown': role_counts,
            'inactive_users': inactive_users,
            'volunteer_statistics': {
                'total_volunteers': total_volunteers,
                'with_profiles': volunteers_with_profiles,
                'with_skills': volunteers_with_skills,
                'profile_completion_rate': round(
                    (volunteers_with_profiles / total_volunteers * 100) 
                    if total_volunteers > 0 else 0, 2
                ),
                'skill_completion_rate': round(
                    (volunteers_with_skills / total_volunteers * 100) 
                    if total_volunteers > 0 else 0, 2
                )
            },
            'recent_registrations': [user.to_dict() for user in recent_users]
        }
    
    @staticmethod
    def block_user(user_id, admin_user, reason=None):
        """
        Block a user account.
        
        Args:
            user_id: ID of the user to block
            admin_user: The admin user performing the action
            reason: Optional reason for blocking
            
        Returns:
            Updated User object
        """
        try:
            user = db.session.get(User, user_id)
            
            if not user:
                raise ValueError("User not found")
            
            if user.role == 'admin':
                raise ValueError("Cannot block admin users")
            
            if not user.is_active:
                raise ValueError("User is already blocked")
            
            # Block the user
            user.is_active = False
            user.updated_at = datetime.now(timezone.utc)
            
            # Cancel any active assignments if user is a volunteer
            if user.role == 'volunteer' and user.volunteer_profile:
                active_assignments = Assignment.query.filter_by(
                    volunteer_id=user.volunteer_profile.id,
                    status='accepted'
                ).all()
                
                for assignment in active_assignments:
                    assignment.cancel("User account blocked by admin")
                
                # Set volunteer as offline
                user.volunteer_profile.availability_status = 'offline'
            
            # Cancel any open emergencies if user is an authority
            if user.role == 'authority':
                open_emergencies = EmergencyRequest.query.filter_by(
                    authority_id=user.id,
                    status='open'
                ).all()
                
                for emergency in open_emergencies:
                    emergency.status = 'cancelled'
                    emergency.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            # Log activity
            log_user_activity(
                action='user_blocked',
                entity_type='user',
                entity_id=user.id,
                details={'reason': reason, 'blocked_by': admin_user.id}
            )
            
            return user
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def unblock_user(user_id, admin_user, reason=None):
        """
        Unblock a user account.
        
        Args:
            user_id: ID of the user to unblock
            admin_user: The admin user performing the action
            reason: Optional reason for unblocking
            
        Returns:
            Updated User object
        """
        try:
            user = db.session.get(User, user_id)
            
            if not user:
                raise ValueError("User not found")
            
            if user.is_active:
                raise ValueError("User is not blocked")
            
            # Unblock the user
            user.is_active = True
            user.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            # Log activity
            log_user_activity(
                action='user_unblocked',
                entity_type='user',
                entity_id=user.id,
                details={'reason': reason, 'unblocked_by': admin_user.id}
            )
            
            return user
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_system_reports(date_range_days=30):
        """
        Generate comprehensive system reports.
        
        Args:
            date_range_days: Number of days to include in the report
            
        Returns:
            Dictionary with system report data
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=date_range_days)
        
        # Emergency statistics
        emergency_stats = {
            'total': EmergencyRequest.query.filter(
                EmergencyRequest.created_at >= start_date
            ).count(),
            'by_status': {},
            'by_priority': {},
            'average_response_time': 0,
            'completion_rate': 0
        }
        
        # Get emergency counts by status and priority
        for status in ['open', 'assigned', 'completed', 'cancelled']:
            count = EmergencyRequest.query.filter(
                EmergencyRequest.created_at >= start_date,
                EmergencyRequest.status == status
            ).count()
            emergency_stats['by_status'][status] = count
        
        for priority in ['low', 'medium', 'high', 'critical']:
            count = EmergencyRequest.query.filter(
                EmergencyRequest.created_at >= start_date,
                EmergencyRequest.priority_level == priority
            ).count()
            emergency_stats['by_priority'][priority] = count
        
        # Assignment statistics
        assignments_in_period = Assignment.query.join(EmergencyRequest).filter(
            EmergencyRequest.created_at >= start_date
        ).all()
        
        assignment_stats = {
            'total': len(assignments_in_period),
            'by_status': {},
            'acceptance_rate': 0,
            'completion_rate': 0,
            'average_response_time': 0
        }
        
        for status in ['requested', 'accepted', 'declined', 'completed', 'cancelled']:
            count = len([a for a in assignments_in_period if a.status == status])
            assignment_stats['by_status'][status] = count
        
        # Calculate rates
        total_responses = assignment_stats['by_status']['accepted'] + assignment_stats['by_status']['declined']
        if total_responses > 0:
            assignment_stats['acceptance_rate'] = round(
                assignment_stats['by_status']['accepted'] / total_responses * 100, 2
            )
        
        if assignment_stats['by_status']['accepted'] > 0:
            assignment_stats['completion_rate'] = round(
                assignment_stats['by_status']['completed'] / assignment_stats['by_status']['accepted'] * 100, 2
            )
        
        # Calculate average response time
        response_times = [a.response_time_minutes for a in assignments_in_period if a.response_time_minutes]
        if response_times:
            assignment_stats['average_response_time'] = round(sum(response_times) / len(response_times), 2)
        
        # User activity statistics
        user_stats = {
            'new_registrations': User.query.filter(User.created_at >= start_date).count(),
            'active_volunteers': VolunteerProfile.query.filter_by(availability_status='available').count(),
            'skill_verifications': VolunteerSkill.query.filter(
                VolunteerSkill.verified_at >= start_date
            ).count()
        }
        
        # System performance metrics
        performance_stats = {
            'total_activity_logs': ActivityLog.query.filter(
                ActivityLog.created_at >= start_date
            ).count(),
            'emergency_escalations': EmergencyRequest.query.filter(
                EmergencyRequest.created_at >= start_date,
                EmergencyRequest.escalation_count > 0
            ).count()
        }
        
        return {
            'report_period': {
                'start_date': start_date.isoformat(),
                'end_date': datetime.now(timezone.utc).isoformat(),
                'days': date_range_days
            },
            'emergency_statistics': emergency_stats,
            'assignment_statistics': assignment_stats,
            'user_statistics': user_stats,
            'performance_statistics': performance_stats,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
    
    @staticmethod
    def get_user_details(user_id):
        """
        Get detailed information about a specific user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary with comprehensive user information
        """
        user = db.session.get(User, user_id)
        if not user:
            return None
        
        user_data = user.to_dict()
        
        # Add role-specific information
        if user.role == 'volunteer' and user.volunteer_profile:
            user_data['volunteer_profile'] = user.volunteer_profile.to_dict()
            user_data['skills'] = [
                vs.to_dict(include_skill=True) 
                for vs in user.volunteer_profile.volunteer_skills
            ]
            user_data['assignments'] = [
                a.to_dict(include_emergency=True) 
                for a in user.volunteer_profile.assignments[:10]  # Last 10 assignments
            ]
        
        elif user.role == 'authority':
            user_data['emergencies'] = [
                e.to_dict() for e in user.created_emergencies[:10]  # Last 10 emergencies
            ]
        
        # Add activity history
        user_data['recent_activity'] = [
            {
                'action': log.action,
                'entity_type': log.entity_type,
                'entity_id': log.entity_id,
                'created_at': log.created_at.isoformat() if log.created_at else None,
                'details': log.details
            }
            for log in user.activity_logs[:20]  # Last 20 activities
        ]
        
        return user_data
    
    @staticmethod
    def _notify_skill_verification_decision(volunteer_skill, decision):
        """
        Send notification to volunteer about skill verification decision.
        
        Args:
            volunteer_skill: The VolunteerSkill object
            decision: 'approved' or 'rejected'
        """
        try:
            volunteer = volunteer_skill.volunteer_profile
            skill = volunteer_skill.skill
            
            notification_data = {
                'type': f'skill_verification_{decision}',
                'volunteer_skill_id': volunteer_skill.id,
                'volunteer_id': volunteer.id,
                'skill_id': skill.id,
                'title': f'Skill Verification {decision.title()}',
                'message': f'Your {skill.name} skill has been {decision}.',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'skill_details': {
                    'name': skill.name,
                    'category': skill.category,
                    'verification_notes': volunteer_skill.verification_notes
                }
            }
            
            # Log notification
            ActivityLog.log_action(
                user_id=volunteer.user_id,
                action='notification_sent',
                entity_type='volunteer_skill',
                entity_id=volunteer_skill.id,
                details=notification_data
            )
            
        except Exception as e:
            print(f"Error sending skill verification notification: {str(e)}")
    
    @staticmethod
    def get_admin_dashboard_data():
        """
        Get comprehensive data for admin dashboard.
        
        Returns:
            Dictionary with admin dashboard data
        """
        # Get pending items that need attention
        pending_verifications = AdminService.get_pending_skill_verifications(limit=10)
        
        # Get recent system activity
        recent_activity = ActivityLog.query.order_by(
            ActivityLog.created_at.desc()
        ).limit(20).all()
        
        # Get system overview statistics
        system_stats = {
            'total_users': User.query.filter_by(is_active=True).count(),
            'total_emergencies': EmergencyRequest.query.count(),
            'pending_verifications': len(pending_verifications),
            'active_assignments': Assignment.query.filter_by(status='accepted').count()
        }
        
        # Get user management overview
        user_overview = AdminService.get_user_management_overview()
        
        # Get skill verification statistics
        verification_stats = AdminService.get_skill_verification_statistics()
        
        return {
            'system_overview': system_stats,
            'user_management': user_overview,
            'skill_verification': verification_stats,
            'pending_verifications': [
                vs.to_dict(include_skill=True, include_volunteer=True) 
                for vs in pending_verifications
            ],
            'recent_activity': [
                {
                    'id': log.id,
                    'user_id': log.user_id,
                    'user_name': log.user.full_name if log.user else 'System',
                    'action': log.action,
                    'entity_type': log.entity_type,
                    'entity_id': log.entity_id,
                    'created_at': log.created_at.isoformat() if log.created_at else None,
                    'details': log.details
                }
                for log in recent_activity
            ]
        }