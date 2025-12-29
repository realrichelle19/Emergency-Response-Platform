"""
Admin routes for the Emergency Response Platform.

This module provides routes for admin users to manage skill verifications,
user accounts, and system oversight.
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from app.admin import bp
from app import db
from app.models import User, VolunteerProfile, VolunteerSkill, Skill, EmergencyRequest, Assignment, ActivityLog
from app.services.admin_service import AdminService
from app.auth.utils import require_role
from datetime import datetime, timedelta
import json

@bp.route('/dashboard')
@login_required
@require_role('admin')
def dashboard():
    """Admin dashboard with system overview and pending tasks."""
    try:
        # Get comprehensive dashboard data
        dashboard_data = AdminService.get_admin_dashboard_data()
        
        return render_template('admin/dashboard.html', **dashboard_data)
        
    except Exception as e:
        flash(f'Error loading admin dashboard: {str(e)}', 'error')
        return render_template('admin/dashboard.html', 
                             system_overview={}, user_management={}, 
                             skill_verification={}, pending_verifications=[], 
                             recent_activity=[])

@bp.route('/skill_verifications')
@login_required
@require_role('admin')
def skill_verifications():
    """Manage skill verification requests."""
    try:
        status_filter = request.args.get('status', 'pending')
        category_filter = request.args.get('category')
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('VERIFICATIONS_PER_PAGE', 20)
        
        # Build query based on filters
        query = VolunteerSkill.query
        
        if status_filter:
            query = query.filter_by(verification_status=status_filter)
        
        if category_filter:
            query = query.join(Skill).filter(Skill.category == category_filter)
        
        # Order by creation date (oldest first for pending, newest first for others)
        if status_filter == 'pending':
            query = query.order_by(VolunteerSkill.created_at.asc())
        else:
            query = query.order_by(VolunteerSkill.verified_at.desc())
        
        verifications = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get skill categories for filter dropdown
        skill_categories = db.session.query(Skill.category).distinct().all()
        categories = [cat[0] for cat in skill_categories]
        
        # Get verification statistics
        verification_stats = AdminService.get_skill_verification_statistics()
        
        return render_template('admin/skill_verifications.html',
                             verifications=verifications,
                             status_filter=status_filter,
                             category_filter=category_filter,
                             categories=categories,
                             verification_stats=verification_stats)
        
    except Exception as e:
        flash(f'Error loading skill verifications: {str(e)}', 'error')
        return render_template('admin/skill_verifications.html', 
                             verifications=None, categories=[], verification_stats={})

@bp.route('/skill_verification/<int:verification_id>')
@login_required
@require_role('admin')
def view_skill_verification(verification_id):
    """View detailed information about a skill verification request."""
    try:
        verification = VolunteerSkill.query.get(verification_id)
        
        if not verification:
            flash('Skill verification request not found.', 'error')
            return redirect(url_for('admin.skill_verifications'))
        
        # Get volunteer's other skills for context
        other_skills = VolunteerSkill.query.filter(
            VolunteerSkill.volunteer_id == verification.volunteer_id,
            VolunteerSkill.id != verification_id
        ).all()
        
        # Get volunteer's assignment history
        assignments = Assignment.query.filter_by(
            volunteer_id=verification.volunteer_id
        ).order_by(Assignment.assigned_at.desc()).limit(10).all()
        
        return render_template('admin/skill_verification_detail.html',
                             verification=verification,
                             other_skills=other_skills,
                             assignments=assignments)
        
    except Exception as e:
        flash(f'Error loading skill verification details: {str(e)}', 'error')
        return redirect(url_for('admin.skill_verifications'))

@bp.route('/skill_verification/<int:verification_id>/approve', methods=['POST'])
@login_required
@require_role('admin')
def approve_skill_verification(verification_id):
    """Approve a skill verification request."""
    try:
        notes = request.form.get('notes', '').strip()
        
        verification = AdminService.approve_skill_verification(
            verification_id, current_user, notes
        )
        
        flash(f'Skill verification approved for {verification.volunteer_profile.user.full_name}!', 'success')
        
        # Redirect based on source
        if request.form.get('source') == 'detail':
            return redirect(url_for('admin.view_skill_verification', verification_id=verification_id))
        else:
            return redirect(url_for('admin.skill_verifications'))
        
    except Exception as e:
        flash(f'Error approving skill verification: {str(e)}', 'error')
        return redirect(url_for('admin.skill_verifications'))

@bp.route('/skill_verification/<int:verification_id>/reject', methods=['POST'])
@login_required
@require_role('admin')
def reject_skill_verification(verification_id):
    """Reject a skill verification request."""
    try:
        notes = request.form.get('notes', '').strip()
        
        if not notes:
            flash('Rejection reason is required.', 'error')
            return redirect(url_for('admin.view_skill_verification', verification_id=verification_id))
        
        verification = AdminService.reject_skill_verification(
            verification_id, current_user, notes
        )
        
        flash(f'Skill verification rejected for {verification.volunteer_profile.user.full_name}.', 'warning')
        
        # Redirect based on source
        if request.form.get('source') == 'detail':
            return redirect(url_for('admin.view_skill_verification', verification_id=verification_id))
        else:
            return redirect(url_for('admin.skill_verifications'))
        
    except Exception as e:
        flash(f'Error rejecting skill verification: {str(e)}', 'error')
        return redirect(url_for('admin.skill_verifications'))

@bp.route('/users')
@login_required
@require_role('admin')
def user_management():
    """User management interface."""
    try:
        role_filter = request.args.get('role')
        status_filter = request.args.get('status', 'active')
        search_query = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('USERS_PER_PAGE', 20)
        
        # Build query based on filters
        query = User.query
        
        if role_filter:
            query = query.filter_by(role=role_filter)
        
        if status_filter == 'active':
            query = query.filter_by(is_active=True)
        elif status_filter == 'blocked':
            query = query.filter_by(is_active=False)
        
        if search_query:
            search_pattern = f'%{search_query}%'
            query = query.filter(
                db.or_(
                    User.email.ilike(search_pattern),
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern)
                )
            )
        
        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get user management overview
        user_overview = AdminService.get_user_management_overview()
        
        return render_template('admin/user_management.html',
                             users=users,
                             role_filter=role_filter,
                             status_filter=status_filter,
                             search_query=search_query,
                             user_overview=user_overview)
        
    except Exception as e:
        flash(f'Error loading user management: {str(e)}', 'error')
        return render_template('admin/user_management.html', 
                             users=None, user_overview={})

@bp.route('/user/<int:user_id>')
@login_required
@require_role('admin')
def view_user(user_id):
    """View detailed information about a specific user."""
    try:
        user_details = AdminService.get_user_details(user_id)
        
        if not user_details:
            flash('User not found.', 'error')
            return redirect(url_for('admin.user_management'))
        
        return render_template('admin/user_detail.html', user_data=user_details)
        
    except Exception as e:
        flash(f'Error loading user details: {str(e)}', 'error')
        return redirect(url_for('admin.user_management'))

@bp.route('/user/<int:user_id>/block', methods=['POST'])
@login_required
@require_role('admin')
def block_user(user_id):
    """Block a user account."""
    try:
        reason = request.form.get('reason', '').strip()
        
        if not reason:
            flash('Reason for blocking is required.', 'error')
            return redirect(url_for('admin.view_user', user_id=user_id))
        
        user = AdminService.block_user(user_id, current_user, reason)
        
        flash(f'User {user.full_name} has been blocked.', 'warning')
        return redirect(url_for('admin.view_user', user_id=user_id))
        
    except Exception as e:
        flash(f'Error blocking user: {str(e)}', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))

@bp.route('/user/<int:user_id>/unblock', methods=['POST'])
@login_required
@require_role('admin')
def unblock_user(user_id):
    """Unblock a user account."""
    try:
        reason = request.form.get('reason', '').strip()
        
        user = AdminService.unblock_user(user_id, current_user, reason)
        
        flash(f'User {user.full_name} has been unblocked.', 'success')
        return redirect(url_for('admin.view_user', user_id=user_id))
        
    except Exception as e:
        flash(f'Error unblocking user: {str(e)}', 'error')
        return redirect(url_for('admin.view_user', user_id=user_id))

@bp.route('/reports')
@login_required
@require_role('admin')
def system_reports():
    """Generate and view system reports."""
    try:
        # Get date range from query parameters
        days = request.args.get('days', 30, type=int)
        
        # Generate comprehensive system reports
        report_data = AdminService.get_system_reports(date_range_days=days)
        
        return render_template('admin/reports.html', 
                             report_data=report_data, days=days)
        
    except Exception as e:
        flash(f'Error generating system reports: {str(e)}', 'error')
        return render_template('admin/reports.html', 
                             report_data={}, days=30)

@bp.route('/activity_logs')
@login_required
@require_role('admin')
def activity_logs():
    """View system activity logs."""
    try:
        action_filter = request.args.get('action')
        user_filter = request.args.get('user_id', type=int)
        entity_filter = request.args.get('entity_type')
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config.get('LOGS_PER_PAGE', 50)
        
        # Build query based on filters
        query = ActivityLog.query
        
        if action_filter:
            query = query.filter_by(action=action_filter)
        
        if user_filter:
            query = query.filter_by(user_id=user_filter)
        
        if entity_filter:
            query = query.filter_by(entity_type=entity_filter)
        
        logs = query.order_by(ActivityLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Get filter options
        actions = db.session.query(ActivityLog.action).distinct().all()
        action_options = [action[0] for action in actions]
        
        entity_types = db.session.query(ActivityLog.entity_type).distinct().all()
        entity_options = [entity[0] for entity in entity_types]
        
        return render_template('admin/activity_logs.html',
                             logs=logs,
                             action_filter=action_filter,
                             user_filter=user_filter,
                             entity_filter=entity_filter,
                             action_options=action_options,
                             entity_options=entity_options)
        
    except Exception as e:
        flash(f'Error loading activity logs: {str(e)}', 'error')
        return render_template('admin/activity_logs.html', 
                             logs=None, action_options=[], entity_options=[])

# API endpoints for AJAX requests
@bp.route('/api/dashboard/stats')
@login_required
@require_role('admin')
def get_dashboard_stats():
    """Get real-time dashboard statistics (AJAX endpoint)."""
    try:
        dashboard_data = AdminService.get_admin_dashboard_data()
        
        # Return only the stats portion for AJAX updates
        stats = {
            'system_overview': dashboard_data['system_overview'],
            'pending_verifications': len(dashboard_data['pending_verifications']),
            'last_updated': datetime.utcnow().isoformat()
        }
        
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/skill_verification/<int:verification_id>/quick_action', methods=['POST'])
@login_required
@require_role('admin')
def quick_skill_verification_action(verification_id):
    """Quick approve/reject skill verification (AJAX endpoint)."""
    try:
        action = request.json.get('action')  # 'approve' or 'reject'
        notes = request.json.get('notes', '')
        
        if action == 'approve':
            verification = AdminService.approve_skill_verification(
                verification_id, current_user, notes
            )
            message = f'Skill approved for {verification.volunteer_profile.user.full_name}'
        elif action == 'reject':
            if not notes:
                return jsonify({'error': 'Rejection reason is required'}), 400
            
            verification = AdminService.reject_skill_verification(
                verification_id, current_user, notes
            )
            message = f'Skill rejected for {verification.volunteer_profile.user.full_name}'
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        return jsonify({
            'success': True,
            'message': message,
            'verification': verification.to_dict(include_skill=True, include_volunteer=True)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/user/<int:user_id>/quick_action', methods=['POST'])
@login_required
@require_role('admin')
def quick_user_action(user_id):
    """Quick block/unblock user (AJAX endpoint)."""
    try:
        action = request.json.get('action')  # 'block' or 'unblock'
        reason = request.json.get('reason', '')
        
        if action == 'block':
            if not reason:
                return jsonify({'error': 'Reason for blocking is required'}), 400
            
            user = AdminService.block_user(user_id, current_user, reason)
            message = f'User {user.full_name} has been blocked'
        elif action == 'unblock':
            user = AdminService.unblock_user(user_id, current_user, reason)
            message = f'User {user.full_name} has been unblocked'
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        return jsonify({
            'success': True,
            'message': message,
            'user': user.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/reports/export')
@login_required
@require_role('admin')
def export_reports():
    """Export system reports as JSON."""
    try:
        days = request.args.get('days', 30, type=int)
        report_data = AdminService.get_system_reports(date_range_days=days)
        
        return jsonify(report_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500