"""
Authority routes for the Emergency Response Platform.

This module provides routes for authority users to manage emergency requests,
view volunteer assignments, and monitor system status.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.authority import bp
from app import db
from app.models import EmergencyRequest, Assignment, Skill, VolunteerProfile, ActivityLog
from app.services.emergency_service import EmergencyService
from app.services.assignment_service import AssignmentService
from app.services.notification_service import NotificationService
from app.auth.utils import require_role
from datetime import datetime, timedelta, timezone
import json

@bp.route('/dashboard')
@login_required
@require_role('authority')
def dashboard():
    """Authority dashboard with emergency overview and statistics."""
    try:
        # Get authority's emergency requests
        emergencies = EmergencyService.get_emergency_requests(
            current_user, limit=10
        )
        
        # Get system overview statistics
        system_stats = EmergencyService.get_system_emergency_overview()
        
        # Get recent activity for this authority
        recent_activity = ActivityLog.query.filter_by(
            user_id=current_user.id
        ).order_by(ActivityLog.created_at.desc()).limit(10).all()
        
        # Get pending assignments for authority's emergencies
        authority_emergency_ids = [e.id for e in emergencies]
        pending_assignments = Assignment.query.filter(
            Assignment.emergency_id.in_(authority_emergency_ids),
            Assignment.status == 'requested'
        ).count() if authority_emergency_ids else 0
        
        # Get active assignments
        active_assignments = Assignment.query.filter(
            Assignment.emergency_id.in_(authority_emergency_ids),
            Assignment.status == 'accepted'
        ).count() if authority_emergency_ids else 0
        
        dashboard_data = {
            'emergencies': emergencies,
            'system_stats': system_stats,
            'recent_activity': recent_activity,
            'pending_assignments': pending_assignments,
            'active_assignments': active_assignments,
            'total_emergencies': len(emergencies)
        }
        
        return render_template('authority/dashboard.html', **dashboard_data)
        
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('authority/dashboard.html', 
                             emergencies=[], system_stats={}, recent_activity=[])

@bp.route('/emergencies')
@login_required
@require_role('authority')
def list_emergencies():
    """List all emergency requests for the current authority."""
    try:
        status_filter = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('EMERGENCIES_PER_PAGE', 20)
        
        # Get emergencies with pagination
        query = EmergencyRequest.query.filter_by(authority_id=current_user.id)
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        emergencies = query.order_by(
            EmergencyRequest.created_at.desc()
        ).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('authority/emergencies.html', 
                             emergencies=emergencies, status_filter=status_filter)
        
    except Exception as e:
        flash(f'Error loading emergencies: {str(e)}', 'error')
        return render_template('authority/emergencies.html', emergencies=None)

@bp.route('/emergency/<int:emergency_id>')
@login_required
@require_role('authority')
def view_emergency(emergency_id):
    """View detailed information about a specific emergency."""
    try:
        emergency = EmergencyService.get_emergency_by_id(emergency_id, current_user)
        
        if not emergency:
            flash('Emergency not found or access denied.', 'error')
            return redirect(url_for('authority.list_emergencies'))
        
        # Get emergency statistics
        emergency_stats = EmergencyService.get_emergency_statistics(emergency_id)
        
        # Get assignments for this emergency
        assignments = AssignmentService.get_emergency_assignments(emergency_id, current_user)
        
        # Get available volunteers in the area (for manual assignment)
        from app.services.matching_service import MatchingService
        available_volunteers = MatchingService.find_matching_volunteers(
            emergency, limit=10
        )
        
        return render_template('authority/emergency_detail.html',
                             emergency=emergency,
                             emergency_stats=emergency_stats,
                             assignments=assignments,
                             available_volunteers=available_volunteers)
        
    except Exception as e:
        flash(f'Error loading emergency details: {str(e)}', 'error')
        return redirect(url_for('authority.list_emergencies'))

@bp.route('/create_emergency', methods=['GET', 'POST'])
@login_required
@require_role('authority')
def create_emergency():
    """Create a new emergency request."""
    if request.method == 'GET':
        # Get available skills for the form
        skills = Skill.query.all()
        return render_template('authority/create_emergency.html', skills=skills)
    
    try:
        # Extract form data
        emergency_data = {
            'title': request.form.get('title', '').strip(),
            'description': request.form.get('description', '').strip(),
            'latitude': float(request.form.get('latitude', 0)),
            'longitude': float(request.form.get('longitude', 0)),
            'address': request.form.get('address', '').strip(),
            'priority_level': request.form.get('priority_level', 'medium'),
            'required_volunteers': int(request.form.get('required_volunteers', 1)),
            'search_radius_km': int(request.form.get('search_radius_km', 10))
        }
        
        # Validate required fields
        if not emergency_data['title']:
            flash('Emergency title is required.', 'error')
            return redirect(url_for('authority.create_emergency'))
        
        if not emergency_data['description']:
            flash('Emergency description is required.', 'error')
            return redirect(url_for('authority.create_emergency'))
        
        # Get required skills
        required_skill_ids = request.form.getlist('required_skills')
        required_skill_ids = [int(sid) for sid in required_skill_ids if sid.isdigit()]
        
        # Create emergency
        emergency = EmergencyService.create_emergency_request(
            current_user, emergency_data, required_skill_ids
        )
        
        flash(f'Emergency "{emergency.title}" created successfully! Volunteers are being notified.', 'success')
        return redirect(url_for('authority.view_emergency', emergency_id=emergency.id))
        
    except ValueError as e:
        flash(f'Invalid input: {str(e)}', 'error')
        return redirect(url_for('authority.create_emergency'))
    except Exception as e:
        flash(f'Error creating emergency: {str(e)}', 'error')
        return redirect(url_for('authority.create_emergency'))

@bp.route('/emergency/<int:emergency_id>/edit', methods=['GET', 'POST'])
@login_required
@require_role('authority')
def edit_emergency(emergency_id):
    """Edit an existing emergency request."""
    try:
        emergency = EmergencyService.get_emergency_by_id(emergency_id, current_user)
        
        if not emergency:
            flash('Emergency not found or access denied.', 'error')
            return redirect(url_for('authority.list_emergencies'))
        
        if request.method == 'GET':
            skills = Skill.query.all()
            return render_template('authority/edit_emergency.html', 
                                 emergency=emergency, skills=skills)
        
        # Handle POST request - update emergency
        update_data = {}
        
        # Update fields if provided
        if request.form.get('title'):
            update_data['title'] = request.form.get('title').strip()
        
        if request.form.get('description'):
            update_data['description'] = request.form.get('description').strip()
        
        if request.form.get('address'):
            update_data['address'] = request.form.get('address').strip()
        
        if request.form.get('priority_level'):
            update_data['priority_level'] = request.form.get('priority_level')
        
        if request.form.get('required_volunteers'):
            update_data['required_volunteers'] = int(request.form.get('required_volunteers'))
        
        if request.form.get('search_radius_km'):
            update_data['search_radius_km'] = int(request.form.get('search_radius_km'))
        
        # Update coordinates if provided
        if request.form.get('latitude') and request.form.get('longitude'):
            update_data['latitude'] = float(request.form.get('latitude'))
            update_data['longitude'] = float(request.form.get('longitude'))
        
        # Update emergency
        updated_emergency = EmergencyService.update_emergency_request(
            emergency_id, current_user, update_data
        )
        
        flash('Emergency updated successfully!', 'success')
        return redirect(url_for('authority.view_emergency', emergency_id=emergency_id))
        
    except Exception as e:
        flash(f'Error updating emergency: {str(e)}', 'error')
        return redirect(url_for('authority.view_emergency', emergency_id=emergency_id))

@bp.route('/emergency/<int:emergency_id>/escalate', methods=['POST'])
@login_required
@require_role('authority')
def escalate_emergency(emergency_id):
    """Escalate an emergency request."""
    try:
        emergency = EmergencyService.escalate_emergency(emergency_id, current_user)
        
        flash(f'Emergency escalated to {emergency.priority_level} priority. '
              f'Search radius expanded to {emergency.search_radius_km}km.', 'success')
        
        return redirect(url_for('authority.view_emergency', emergency_id=emergency_id))
        
    except Exception as e:
        flash(f'Error escalating emergency: {str(e)}', 'error')
        return redirect(url_for('authority.view_emergency', emergency_id=emergency_id))

@bp.route('/emergency/<int:emergency_id>/complete', methods=['POST'])
@login_required
@require_role('authority')
def complete_emergency(emergency_id):
    """Mark an emergency as completed."""
    try:
        completion_notes = request.form.get('completion_notes', '')
        
        emergency = EmergencyService.complete_emergency(
            emergency_id, current_user, completion_notes
        )
        
        flash('Emergency marked as completed successfully!', 'success')
        return redirect(url_for('authority.view_emergency', emergency_id=emergency_id))
        
    except Exception as e:
        flash(f'Error completing emergency: {str(e)}', 'error')
        return redirect(url_for('authority.view_emergency', emergency_id=emergency_id))

@bp.route('/emergency/<int:emergency_id>/cancel', methods=['POST'])
@login_required
@require_role('authority')
def cancel_emergency(emergency_id):
    """Cancel an emergency request."""
    try:
        reason = request.form.get('reason', '')
        
        emergency = EmergencyService.cancel_emergency(
            emergency_id, current_user, reason
        )
        
        flash('Emergency cancelled successfully.', 'success')
        return redirect(url_for('authority.view_emergency', emergency_id=emergency_id))
        
    except Exception as e:
        flash(f'Error cancelling emergency: {str(e)}', 'error')
        return redirect(url_for('authority.view_emergency', emergency_id=emergency_id))

@bp.route('/emergency/<int:emergency_id>/assign_volunteer', methods=['POST'])
@login_required
@require_role('authority')
def assign_volunteer_manually(emergency_id):
    """Manually assign a volunteer to an emergency."""
    try:
        volunteer_id = request.form.get('volunteer_id')
        
        if not volunteer_id:
            flash('Please select a volunteer to assign.', 'error')
            return redirect(url_for('authority.view_emergency', emergency_id=emergency_id))
        
        assignment = EmergencyService.assign_volunteer_manually(
            emergency_id, int(volunteer_id), current_user
        )
        
        flash('Volunteer assigned successfully! They will be notified.', 'success')
        return redirect(url_for('authority.view_emergency', emergency_id=emergency_id))
        
    except Exception as e:
        flash(f'Error assigning volunteer: {str(e)}', 'error')
        return redirect(url_for('authority.view_emergency', emergency_id=emergency_id))

@bp.route('/assignments')
@login_required
@require_role('authority')
def list_assignments():
    """List all assignments for the authority's emergencies."""
    try:
        status_filter = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('ASSIGNMENTS_PER_PAGE', 20)
        
        # Get authority's emergency IDs
        authority_emergency_ids = [e.id for e in EmergencyRequest.query.filter_by(
            authority_id=current_user.id
        ).all()]
        
        if not authority_emergency_ids:
            return render_template('authority/assignments.html', assignments=None)
        
        # Get assignments for authority's emergencies
        query = Assignment.query.filter(
            Assignment.emergency_id.in_(authority_emergency_ids)
        )
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        assignments = query.order_by(
            Assignment.assigned_at.desc()
        ).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('authority/assignments.html', 
                             assignments=assignments, status_filter=status_filter)
        
    except Exception as e:
        flash(f'Error loading assignments: {str(e)}', 'error')
        return render_template('authority/assignments.html', assignments=None)

@bp.route('/notifications')
@login_required
@require_role('authority')
def notifications():
    """View notifications for the authority."""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        notifications = NotificationService.get_authority_notifications(
            current_user, limit=limit
        )
        
        # Get notification statistics
        notification_stats = NotificationService.get_notification_statistics(current_user)
        
        return render_template('authority/notifications.html',
                             notifications=notifications,
                             notification_stats=notification_stats)
        
    except Exception as e:
        flash(f'Error loading notifications: {str(e)}', 'error')
        return render_template('authority/notifications.html', 
                             notifications=[], notification_stats={})

@bp.route('/reports')
@login_required
@require_role('authority')
def reports():
    """Generate reports and analytics for the authority."""
    try:
        # Get date range from query parameters
        days = request.args.get('days', 30, type=int)
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get authority's emergencies in date range
        emergencies = EmergencyRequest.query.filter(
            EmergencyRequest.authority_id == current_user.id,
            EmergencyRequest.created_at >= start_date
        ).all()
        
        # Calculate statistics
        total_emergencies = len(emergencies)
        status_breakdown = {}
        priority_breakdown = {}
        
        for emergency in emergencies:
            # Status breakdown
            status = emergency.status
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
            
            # Priority breakdown
            priority = emergency.priority_level
            priority_breakdown[priority] = priority_breakdown.get(priority, 0) + 1
        
        # Get assignment statistics
        emergency_ids = [e.id for e in emergencies]
        assignments = Assignment.query.filter(
            Assignment.emergency_id.in_(emergency_ids)
        ).all() if emergency_ids else []
        
        assignment_stats = {
            'total_assignments': len(assignments),
            'accepted': len([a for a in assignments if a.status == 'accepted']),
            'declined': len([a for a in assignments if a.status == 'declined']),
            'completed': len([a for a in assignments if a.status == 'completed']),
            'cancelled': len([a for a in assignments if a.status == 'cancelled'])
        }
        
        # Calculate response times
        response_times = [a.response_time_minutes for a in assignments if a.response_time_minutes]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        report_data = {
            'date_range': {
                'start_date': start_date,
                'end_date': datetime.now(timezone.utc),
                'days': days
            },
            'emergency_stats': {
                'total': total_emergencies,
                'status_breakdown': status_breakdown,
                'priority_breakdown': priority_breakdown
            },
            'assignment_stats': assignment_stats,
            'performance_metrics': {
                'average_response_time_minutes': round(avg_response_time, 2),
                'acceptance_rate': round(
                    (assignment_stats['accepted'] / len(assignments) * 100) 
                    if assignments else 0, 2
                ),
                'completion_rate': round(
                    (assignment_stats['completed'] / assignment_stats['accepted'] * 100) 
                    if assignment_stats['accepted'] > 0 else 0, 2
                )
            },
            'recent_emergencies': emergencies[:10]
        }
        
        return render_template('authority/reports.html', **report_data)
        
    except Exception as e:
        flash(f'Error generating reports: {str(e)}', 'error')
        return render_template('authority/reports.html', 
                             emergency_stats={}, assignment_stats={}, 
                             performance_metrics={}, recent_emergencies=[])

# API endpoints for AJAX requests
@bp.route('/assignment/<int:assignment_id>/cancel', methods=['POST'])
@login_required
@require_role('authority')
def cancel_assignment(assignment_id):
    """Cancel a volunteer assignment."""
    try:
        reason = request.form.get('reason', '')
        
        assignment = AssignmentService.cancel_assignment(
            assignment_id, current_user, reason
        )
        
        flash('Assignment cancelled successfully. The volunteer has been notified.', 'success')
        return redirect(url_for('authority.list_assignments'))
        
    except Exception as e:
        flash(f'Error cancelling assignment: {str(e)}', 'error')
        return redirect(url_for('authority.list_assignments'))

@bp.route('/api/emergency/<int:emergency_id>/status')
@login_required
@require_role('authority')
def get_emergency_status(emergency_id):
    """Get real-time status of an emergency (AJAX endpoint)."""
    try:
        emergency = EmergencyService.get_emergency_by_id(emergency_id, current_user)
        
        if not emergency:
            return jsonify({'error': 'Emergency not found'}), 404
        
        # Get current assignments
        assignments = AssignmentService.get_emergency_assignments(emergency_id, current_user)
        
        status_data = {
            'emergency': {
                'id': emergency.id,
                'status': emergency.status,
                'priority_level': emergency.priority_level,
                'escalation_count': emergency.escalation_count,
                'volunteers_needed': emergency.volunteers_needed,
                'expires_at': emergency.expires_at.isoformat() if emergency.expires_at else None
            },
            'assignments': {
                'total': len(assignments),
                'requested': len([a for a in assignments if a.status == 'requested']),
                'accepted': len([a for a in assignments if a.status == 'accepted']),
                'declined': len([a for a in assignments if a.status == 'declined']),
                'completed': len([a for a in assignments if a.status == 'completed'])
            },
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify(status_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/dashboard/stats')
@login_required
@require_role('authority')
def get_dashboard_stats():
    """Get real-time dashboard statistics (AJAX endpoint)."""
    try:
        # Get authority's emergency counts
        emergency_counts = {
            'open': EmergencyRequest.query.filter_by(
                authority_id=current_user.id, status='open'
            ).count(),
            'assigned': EmergencyRequest.query.filter_by(
                authority_id=current_user.id, status='assigned'
            ).count(),
            'completed': EmergencyRequest.query.filter_by(
                authority_id=current_user.id, status='completed'
            ).count(),
            'cancelled': EmergencyRequest.query.filter_by(
                authority_id=current_user.id, status='cancelled'
            ).count()
        }
        
        # Get assignment counts for authority's emergencies
        authority_emergency_ids = [e.id for e in EmergencyRequest.query.filter_by(
            authority_id=current_user.id
        ).all()]
        
        assignment_counts = {
            'pending': 0,
            'active': 0,
            'completed': 0
        }
        
        if authority_emergency_ids:
            assignment_counts['pending'] = Assignment.query.filter(
                Assignment.emergency_id.in_(authority_emergency_ids),
                Assignment.status == 'requested'
            ).count()
            
            assignment_counts['active'] = Assignment.query.filter(
                Assignment.emergency_id.in_(authority_emergency_ids),
                Assignment.status == 'accepted'
            ).count()
            
            assignment_counts['completed'] = Assignment.query.filter(
                Assignment.emergency_id.in_(authority_emergency_ids),
                Assignment.status == 'completed'
            ).count()
        
        stats = {
            'emergencies': emergency_counts,
            'assignments': assignment_counts,
            'total_emergencies': sum(emergency_counts.values()),
            'total_assignments': sum(assignment_counts.values()),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
