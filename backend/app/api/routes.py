"""
API routes for the Emergency Response Platform.

This module provides RESTful API endpoints for real-time updates,
system status, and cross-platform integration.
"""

from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from app.api import bp
from app.services.realtime_service import RealtimeService
from app.auth.utils import require_role, require_roles
from datetime import datetime, timedelta
import json

@bp.route('/status')
def status():
    """API status endpoint."""
    return {
        "status": "API ready", 
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@bp.route('/health')
def health():
    """System health status endpoint."""
    try:
        health_status = RealtimeService.get_system_health_status()
        return jsonify(health_status)
    except Exception as e:
        return jsonify({
            'error': 'Health check failed',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Real-time update endpoints
@bp.route('/updates/volunteer')
@login_required
@require_role('volunteer')
def volunteer_updates():
    """Get real-time updates for volunteer users."""
    try:
        last_update = request.args.get('since')
        last_update_time = None
        
        if last_update:
            try:
                last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid timestamp format'}), 400
        
        updates = RealtimeService.get_volunteer_updates(current_user, last_update_time)
        return jsonify(updates)
        
    except Exception as e:
        current_app.logger.error(f"Error getting volunteer updates: {str(e)}")
        return jsonify({
            'error': 'Failed to get updates',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@bp.route('/updates/authority')
@login_required
@require_role('authority')
def authority_updates():
    """Get real-time updates for authority users."""
    try:
        last_update = request.args.get('since')
        last_update_time = None
        
        if last_update:
            try:
                last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid timestamp format'}), 400
        
        updates = RealtimeService.get_authority_updates(current_user, last_update_time)
        return jsonify(updates)
        
    except Exception as e:
        current_app.logger.error(f"Error getting authority updates: {str(e)}")
        return jsonify({
            'error': 'Failed to get updates',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@bp.route('/updates/admin')
@login_required
@require_role('admin')
def admin_updates():
    """Get real-time updates for admin users."""
    try:
        last_update = request.args.get('since')
        last_update_time = None
        
        if last_update:
            try:
                last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid timestamp format'}), 400
        
        updates = RealtimeService.get_admin_updates(current_user, last_update_time)
        return jsonify(updates)
        
    except Exception as e:
        current_app.logger.error(f"Error getting admin updates: {str(e)}")
        return jsonify({
            'error': 'Failed to get updates',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# System monitoring endpoints
@bp.route('/monitoring/notifications')
@login_required
@require_role('admin')
def notification_monitoring():
    """Get notification delivery performance metrics."""
    try:
        delivery_stats = RealtimeService.check_notification_delivery_timing()
        return jsonify(delivery_stats)
        
    except Exception as e:
        current_app.logger.error(f"Error getting notification monitoring: {str(e)}")
        return jsonify({
            'error': 'Failed to get notification metrics',
            'message': str(e)
        }), 500

@bp.route('/system/escalate', methods=['POST'])
@login_required
@require_role('admin')
def trigger_escalations():
    """Manually trigger emergency escalation check."""
    try:
        escalated_ids = RealtimeService.trigger_emergency_escalations()
        return jsonify({
            'escalated_emergencies': escalated_ids,
            'count': len(escalated_ids),
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error triggering escalations: {str(e)}")
        return jsonify({
            'error': 'Failed to trigger escalations',
            'message': str(e)
        }), 500

# Polling configuration endpoint
@bp.route('/config/polling')
@login_required
def polling_config():
    """Get polling configuration for the current user."""
    try:
        config = {
            'polling_interval_seconds': current_app.config.get('POLLING_INTERVAL_SECONDS', 30),
            'notification_timeout_minutes': current_app.config.get('NOTIFICATION_TIMEOUT_MINUTES', 1),
            'escalation_timeout_minutes': current_app.config.get('ESCALATION_TIMEOUT_MINUTES', 30),
            'user_role': current_user.role,
            'endpoints': {
                'volunteer': '/api/updates/volunteer',
                'authority': '/api/updates/authority',
                'admin': '/api/updates/admin'
            }
        }
        
        return jsonify(config)
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to get polling config',
            'message': str(e)
        }), 500

# WebSocket-style long polling endpoint
@bp.route('/poll')
@login_required
def long_poll():
    """Long polling endpoint for real-time updates."""
    try:
        timeout = min(int(request.args.get('timeout', 30)), 60)  # Max 60 seconds
        last_update = request.args.get('since')
        last_update_time = None
        
        if last_update:
            try:
                last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            except ValueError:
                return jsonify({'error': 'Invalid timestamp format'}), 400
        
        # Get updates based on user role
        if current_user.role == 'volunteer':
            updates = RealtimeService.get_volunteer_updates(current_user, last_update_time)
        elif current_user.role == 'authority':
            updates = RealtimeService.get_authority_updates(current_user, last_update_time)
        elif current_user.role == 'admin':
            updates = RealtimeService.get_admin_updates(current_user, last_update_time)
        else:
            return jsonify({'error': 'Invalid user role'}), 403
        
        # Check if there are any updates
        has_updates = any([
            updates.get('new_assignments', []),
            updates.get('assignment_updates', []),
            updates.get('emergency_updates', []),
            updates.get('assignment_responses', []),
            updates.get('notifications', []),
            updates.get('system_alerts', []),
            updates.get('system_messages', [])
        ])
        
        if has_updates or timeout <= 0:
            return jsonify(updates)
        
        # For simplicity, we'll return immediately rather than implement true long polling
        # In a production system, you'd want to use WebSockets or Server-Sent Events
        return jsonify(updates)
        
    except Exception as e:
        current_app.logger.error(f"Error in long polling: {str(e)}")
        return jsonify({
            'error': 'Polling failed',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500