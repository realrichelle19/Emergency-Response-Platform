"""
Complete API endpoints for Emergency Response Platform.
All REST API endpoints in one organized file.
"""

from flask import request, jsonify, current_app
from flask_jwt_extended import (
    jwt_required, get_jwt_identity, get_jwt,
    create_access_token, create_refresh_token
)
from app.api import bp
from app.models import *
from app import db
from app.services.emergency_service import EmergencyService
from app.services.assignment_service import AssignmentService
from app.services.admin_service import AdminService
from app.services.realtime_service import RealtimeService
from app.auth.utils import check_password, validate_password_strength
from datetime import datetime, timezone, timedelta

# ============================================================================
# AUTHENTICATION API
# ============================================================================

@bp.route('/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name', 'role']
        for field in required_fields:
            if not data.get(field):
                return api_response(error=f'{field} is required', status=400)
        
        # Validate password strength
        password_errors = validate_password_strength(data['password'])
        if password_errors:
            return api_response(error='Password validation failed', status=400)
        
        # Check if user already exists
        if User.query.filter_by(email=data['email']).first():
            return api_response(error='Email already registered', status=409)
        
        # Validate role
        if data['role'] not in ['volunteer', 'authority', 'admin']:
            return api_response(error='Invalid role', status=400)
        
        # Create new user
        user = User(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data['role'],
            phone=data.get('phone')
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Create tokens
        access_token = create_access_token(
            identity=user.id,
            additional_claims={'role': user.role}
        )
        refresh_token = create_refresh_token(identity=user.id)
        
        return api_response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }, 'User registered successfully', status=201)
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

@bp.route('/auth/login', methods=['POST'])
def login():
    """Authenticate user and return JWT tokens."""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return api_response(error='Email and password are required', status=400)
        
        # Find user
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not user.check_password(data['password']):
            return api_response(error='Invalid email or password', status=401)
        
        if not user.is_active:
            return api_response(error='Account is deactivated', status=403)
        
        # Create tokens
        access_token = create_access_token(
            identity=user.id,
            additional_claims={'role': user.role}
        )
        refresh_token = create_refresh_token(identity=user.id)
        
        return api_response({
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }, 'Login successful')
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token."""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return api_response(error='User not found or inactive', status=404)
        
        new_token = create_access_token(
            identity=current_user_id,
            additional_claims={'role': user.role}
        )
        
        return api_response({'access_token': new_token})
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (blacklist token)."""
    try:
        jti = get_jwt()['jti']
        # In a real app, you'd add this to a blacklist/redis
        # For now, just return success
        return api_response(message='Successfully logged out')
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile."""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return api_response(error='User not found', status=404)
        
        user_data = user.to_dict()
        if user.volunteer_profile:
            user_data['volunteer_profile'] = user.volunteer_profile.to_dict()
        
        return api_response({'user': user_data})
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/auth/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password."""
    try:
        data = request.get_json()
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return api_response(error='User not found', status=404)
        
        if not data.get('current_password') or not data.get('new_password'):
            return api_response(error='Current password and new password are required', status=400)
        
        # Verify current password
        if not user.check_password(data['current_password']):
            return api_response(error='Current password is incorrect', status=400)
        
        # Validate new password strength
        password_errors = validate_password_strength(data['new_password'])
        if password_errors:
            return api_response(error='Password validation failed', status=400)
        
        # Update password
        user.set_password(data['new_password'])
        db.session.commit()
        
        return api_response(message='Password changed successfully')
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

# ============================================================================
# STATUS AND HEALTH API
# ============================================================================

@bp.route('/status')
def status():
    """API status endpoint."""
    return api_response({
        "status": "API ready", 
        "version": "1.0",
        "timestamp": datetime.utcnow().isoformat()
    })

@bp.route('/health')
def health():
    """System health status endpoint."""
    try:
        health_status = RealtimeService.get_system_health_status()
        return api_response(health_status)
    except Exception as e:
        return api_response(error=str(e), status=500)

# Real-time update endpoints
@bp.route('/updates/volunteer')
@jwt_required()
def volunteer_updates():
    """Get real-time updates for volunteer users."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        last_update = request.args.get('since')
        last_update_time = parse_datetime_param(last_update)
        
        if last_update and last_update_time is None:
            return api_response(error='Invalid timestamp format', status=400)
        
        updates = RealtimeService.get_volunteer_updates(user, last_update_time)
        return api_response(updates)
        
    except Exception as e:
        current_app.logger.error(f"Error getting volunteer updates: {str(e)}")
        return api_response(error=str(e), status=500)

@bp.route('/updates/authority')
@jwt_required()
def authority_updates():
    """Get real-time updates for authority users."""
    try:
        role_check = require_role('authority')
        if role_check:
            return role_check
            
        user = get_current_user()
        last_update = request.args.get('since')
        last_update_time = parse_datetime_param(last_update)
        
        if last_update and last_update_time is None:
            return api_response(error='Invalid timestamp format', status=400)
        
        updates = RealtimeService.get_authority_updates(user, last_update_time)
        return api_response(updates)
        
    except Exception as e:
        current_app.logger.error(f"Error getting authority updates: {str(e)}")
        return api_response(error=str(e), status=500)

@bp.route('/updates/admin')
@jwt_required()
def admin_updates():
    """Get real-time updates for admin users."""
    try:
        role_check = require_role('admin')
        if role_check:
            return role_check
            
        user = get_current_user()
        last_update = request.args.get('since')
        last_update_time = parse_datetime_param(last_update)
        
        if last_update and last_update_time is None:
            return api_response(error='Invalid timestamp format', status=400)
        
        updates = RealtimeService.get_admin_updates(user, last_update_time)
        return api_response(updates)
        
    except Exception as e:
        current_app.logger.error(f"Error getting admin updates: {str(e)}")
        return api_response(error=str(e), status=500)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def parse_datetime_param(datetime_str):
    """Parse datetime parameter with proper timezone handling."""
    if not datetime_str:
        return None
    
    try:
        # Handle both ISO format with and without timezone
        if datetime_str.endswith('Z'):
            datetime_str = datetime_str[:-1] + '+00:00'
        
        parsed_dt = datetime.fromisoformat(datetime_str)
        
        # Ensure timezone awareness
        if parsed_dt.tzinfo is None:
            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
        
        return parsed_dt
    except ValueError:
        return None

def require_role(required_role):
    """Check if current user has required role."""
    claims = get_jwt()
    if claims.get('role') != required_role:
        return jsonify({'error': f'{required_role} role required'}), 403
    return None

def get_current_user():
    """Get current authenticated user."""
    user_id = get_jwt_identity()
    return User.query.get(user_id)

def api_response(data=None, message=None, error=None, status=200):
    """Standard API response format."""
    response = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'success': error is None
    }
    
    if data is not None:
        response['data'] = data
    if message:
        response['message'] = message
    if error:
        response['error'] = error
    
    return jsonify(response), status

# ============================================================================
# VOLUNTEER PROFILE API
# ============================================================================

@bp.route('/volunteers/profile', methods=['GET'])
@jwt_required()
def get_volunteer_profile():
    """Get volunteer profile."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        profile_data = user.volunteer_profile.to_dict(include_user=True)
        profile_data['skills'] = [
            vs.to_dict(include_skill=True) for vs in user.volunteer_profile.volunteer_skills
        ]
        
        return api_response({'profile': profile_data})
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/profile', methods=['POST', 'PUT'])
@jwt_required()
def update_volunteer_profile():
    """Create or update volunteer profile."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        data = request.get_json()
        
        if not user:
            return api_response(error='User not found', status=404)
        
        # Update or create profile using service
        from app.volunteer.services import VolunteerService
        success = VolunteerService.update_profile(user, data)
        
        if success:
            return api_response(message='Profile updated successfully')
        else:
            return api_response(error='Failed to update profile', status=400)
            
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/availability', methods=['PUT'])
@jwt_required()
def update_availability():
    """Update volunteer availability status."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        status = data.get('status')
        if status not in ['available', 'busy', 'offline']:
            return api_response(error='Invalid availability status', status=400)
        
        from app.volunteer.services import VolunteerService
        success = VolunteerService.update_availability(user, status)
        
        if success:
            return api_response(message='Availability updated successfully')
        else:
            return api_response(error='Failed to update availability', status=400)
            
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/skills', methods=['GET'])
@jwt_required()
def get_volunteer_skills():
    """Get volunteer skills."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        skills = [
            vs.to_dict(include_skill=True) 
            for vs in user.volunteer_profile.volunteer_skills
        ]
        
        return api_response({'skills': skills})
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/skills', methods=['POST'])
@jwt_required()
def add_volunteer_skill():
    """Add a skill to volunteer profile."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        skill_id = data.get('skill_id')
        if not skill_id:
            return api_response(error='skill_id is required', status=400)
        
        # Check if skill exists
        skill = Skill.query.get(skill_id)
        if not skill:
            return api_response(error='Skill not found', status=404)
        
        # Check if already added
        existing = VolunteerSkill.query.filter_by(
            volunteer_id=user.volunteer_profile.id,
            skill_id=skill_id
        ).first()
        
        if existing:
            return api_response(error='Skill already added', status=409)
        
        # Add skill
        volunteer_skill = VolunteerSkill(
            volunteer_id=user.volunteer_profile.id,
            skill_id=skill_id,
            verification_status='pending'
        )
        
        db.session.add(volunteer_skill)
        db.session.commit()
        
        return api_response(
            volunteer_skill.to_dict(include_skill=True),
            'Skill added successfully',
            status=201
        )
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/assignments', methods=['GET'])
@jwt_required()
def get_volunteer_assignments():
    """Get volunteer assignments."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        status_filter = request.args.get('status')
        
        query = Assignment.query.filter_by(volunteer_id=user.volunteer_profile.id)
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        assignments = query.order_by(Assignment.assigned_at.desc()).all()
        
        return api_response({
            'assignments': [
                assignment.to_dict(include_emergency=True) 
                for assignment in assignments
            ]
        })
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/assignments/<int:assignment_id>/respond', methods=['PUT'])
@jwt_required()
def respond_to_assignment(assignment_id):
    """Accept or decline an assignment."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return api_response(error='Assignment not found', status=404)
        
        if assignment.volunteer_id != user.volunteer_profile.id:
            return api_response(error='Access denied', status=403)
        
        response = data.get('response')
        if response not in ['accepted', 'declined']:
            return api_response(error='Invalid response. Must be "accepted" or "declined"', status=400)
        
        notes = data.get('notes')
        
        if response == 'accepted':
            assignment.accept(notes)
        else:
            assignment.decline(notes)
        
        db.session.commit()
        
        return api_response(
            assignment.to_dict(include_emergency=True),
            f'Assignment {response} successfully'
        )
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/assignments/<int:assignment_id>/complete', methods=['PUT'])
@jwt_required()
def complete_volunteer_assignment(assignment_id):
    """Mark assignment as completed."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return api_response(error='Assignment not found', status=404)
        
        if assignment.volunteer_id != user.volunteer_profile.id:
            return api_response(error='Access denied', status=403)
        
        if assignment.status != 'accepted':
            return api_response(error='Can only complete accepted assignments', status=400)
        
        notes = data.get('notes')
        assignment.complete(notes)
        db.session.commit()
        
        return api_response(
            assignment.to_dict(include_emergency=True),
            'Assignment completed successfully'
        )
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

# ============================================================================
# SKILLS API
# ============================================================================

@bp.route('/skills', methods=['GET'])
@jwt_required()
def get_all_skills():
    """Get all available skills."""
    try:
        category = request.args.get('category')
        
        query = Skill.query
        if category:
            query = query.filter_by(category=category)
        
        skills = query.order_by(Skill.name).all()
        
        return api_response([skill.to_dict() for skill in skills])
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/skills/categories', methods=['GET'])
@jwt_required()
def get_skill_categories():
    """Get all skill categories."""
    try:
        categories = db.session.query(Skill.category).distinct().all()
        return api_response([cat[0] for cat in categories])
        
    except Exception as e:
        return api_response(error=str(e), status=500)

# ============================================================================
# EMERGENCY REQUESTS API
# ============================================================================

@bp.route('/emergencies', methods=['GET'])
@jwt_required()
def get_emergencies():
    """Get emergency requests with filtering."""
    try:
        user = get_current_user()
        claims = get_jwt()
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')
        priority = request.args.get('priority')
        
        query = EmergencyRequest.query
        
        # Role-based filtering
        if claims.get('role') == 'authority':
            query = query.filter_by(authority_id=user.id)
        elif claims.get('role') == 'volunteer':
            query = query.filter_by(status='open')
        
        if status:
            query = query.filter_by(status=status)
        if priority:
            query = query.filter_by(priority_level=priority)
        
        emergencies = query.order_by(
            EmergencyRequest.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return api_response({
            'emergencies': [e.to_dict(include_authority=True, include_skills=True) 
                          for e in emergencies.items],
            'pagination': {
                'page': page,
                'pages': emergencies.pages,
                'per_page': per_page,
                'total': emergencies.total
            }
        })
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/emergencies', methods=['POST'])
@jwt_required()
def create_emergency():
    """Create new emergency request."""
    try:
        role_check = require_role('authority')
        if role_check:
            return role_check
        
        user = get_current_user()
        data = request.get_json()
        
        # Validate required fields
        required = ['title', 'description', 'latitude', 'longitude', 'priority_level']
        for field in required:
            if not data.get(field):
                return api_response(error=f'{field} is required', status=400)
        
        emergency = EmergencyService.create_emergency_request(
            authority_user=user,
            title=data['title'],
            description=data['description'],
            latitude=data['latitude'],
            longitude=data['longitude'],
            priority_level=data['priority_level'],
            address=data.get('address'),
            required_volunteers=data.get('required_volunteers', 1),
            search_radius_km=data.get('search_radius_km', 10),
            required_skill_ids=data.get('required_skill_ids', [])
        )
        
        return api_response(
            emergency.to_dict(include_authority=True, include_skills=True),
            'Emergency created successfully',
            status=201
        )
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/emergencies/<int:emergency_id>', methods=['GET'])
@jwt_required()
def get_emergency(emergency_id):
    """Get specific emergency details."""
    try:
        user = get_current_user()
        claims = get_jwt()
        
        emergency = EmergencyRequest.query.get(emergency_id)
        if not emergency:
            return api_response(error='Emergency not found', status=404)
        
        # Access control
        if claims.get('role') == 'authority' and emergency.authority_id != user.id:
            return api_response(error='Access denied', status=403)
        
        return api_response(
            emergency.to_dict(include_authority=True, include_skills=True, include_assignments=True)
        )
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/emergencies/<int:emergency_id>/escalate', methods=['POST'])
@jwt_required()
def escalate_emergency(emergency_id):
    """Escalate emergency priority."""
    try:
        user = get_current_user()
        claims = get_jwt()
        
        if claims.get('role') not in ['authority', 'admin']:
            return api_response(error='Authority or admin role required', status=403)
        
        emergency = EmergencyRequest.query.get(emergency_id)
        if not emergency:
            return api_response(error='Emergency not found', status=404)
        
        if claims.get('role') == 'authority' and emergency.authority_id != user.id:
            return api_response(error='Access denied', status=403)
        
        escalated = EmergencyService.escalate_emergency(emergency_id)
        if escalated:
            return api_response(
                escalated.to_dict(include_authority=True, include_skills=True),
                'Emergency escalated successfully'
            )
        else:
            return api_response(error='Failed to escalate emergency', status=400)
            
    except Exception as e:
        return api_response(error=str(e), status=500)

# ============================================================================
# ASSIGNMENTS API
# ============================================================================

@bp.route('/assignments', methods=['GET'])
@jwt_required()
def get_assignments():
    """Get assignments with filtering."""
    try:
        user = get_current_user()
        claims = get_jwt()
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status')
        
        query = Assignment.query
        
        # Role-based filtering
        if claims.get('role') == 'volunteer':
            if user.volunteer_profile:
                query = query.filter_by(volunteer_id=user.volunteer_profile.id)
            else:
                return api_response({'assignments': [], 'pagination': {}})
        elif claims.get('role') == 'authority':
            query = query.join(EmergencyRequest).filter_by(authority_id=user.id)
        
        if status:
            query = query.filter_by(status=status)
        
        assignments = query.order_by(
            Assignment.assigned_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return api_response({
            'assignments': [a.to_dict(include_emergency=True, include_volunteer=True) 
                          for a in assignments.items],
            'pagination': {
                'page': page,
                'pages': assignments.pages,
                'per_page': per_page,
                'total': assignments.total
            }
        })
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/assignments/<int:assignment_id>/accept', methods=['POST'])
@jwt_required()
def accept_assignment(assignment_id):
    """Accept an assignment."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
        
        user = get_current_user()
        data = request.get_json() or {}
        
        success = AssignmentService.accept_assignment(
            assignment_id, user, data.get('notes')
        )
        
        if success:
            return api_response(message='Assignment accepted successfully')
        else:
            return api_response(error='Failed to accept assignment', status=400)
            
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/assignments/<int:assignment_id>/decline', methods=['POST'])
@jwt_required()
def decline_assignment(assignment_id):
    """Decline an assignment."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
        
        user = get_current_user()
        data = request.get_json() or {}
        
        success = AssignmentService.decline_assignment(
            assignment_id, user, data.get('notes')
        )
        
        if success:
            return api_response(message='Assignment declined successfully')
        else:
            return api_response(error='Failed to decline assignment', status=400)
            
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/assignments/<int:assignment_id>/complete', methods=['POST'])
@jwt_required()
def complete_assignment(assignment_id):
    """Complete an assignment."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
        
        user = get_current_user()
        data = request.get_json() or {}
        
        success = AssignmentService.complete_assignment(
            assignment_id, user, data.get('notes')
        )
        
        if success:
            return api_response(message='Assignment completed successfully')
        else:
            return api_response(error='Failed to complete assignment', status=400)
            
    except Exception as e:
        return api_response(error=str(e), status=500)

# ============================================================================
# ADMIN API
# ============================================================================

@bp.route('/admin/users', methods=['GET'])
@jwt_required()
def get_users():
    """Get all users (admin only)."""
    try:
        role_check = require_role('admin')
        if role_check:
            return role_check
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        role_filter = request.args.get('role')
        
        query = User.query
        if role_filter:
            query = query.filter_by(role=role_filter)
        
        users = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return api_response({
            'users': [user.to_dict() for user in users.items],
            'pagination': {
                'page': page,
                'pages': users.pages,
                'per_page': per_page,
                'total': users.total
            }
        })
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/admin/skill-verifications', methods=['GET'])
@jwt_required()
def get_skill_verifications():
    """Get skill verification requests (admin only)."""
    try:
        role_check = require_role('admin')
        if role_check:
            return role_check
        
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        status = request.args.get('status', 'pending')
        
        verifications = VolunteerSkill.query.filter_by(
            verification_status=status
        ).order_by(
            VolunteerSkill.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        return api_response({
            'verifications': [
                v.to_dict(include_skill=True, include_volunteer=True) 
                for v in verifications.items
            ],
            'pagination': {
                'page': page,
                'pages': verifications.pages,
                'per_page': per_page,
                'total': verifications.total
            }
        })
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/admin/skill-verifications/<int:verification_id>/approve', methods=['POST'])
@jwt_required()
def approve_skill_verification(verification_id):
    """Approve skill verification (admin only)."""
    try:
        role_check = require_role('admin')
        if role_check:
            return role_check
        
        user = get_current_user()
        data = request.get_json() or {}
        
        verification = AdminService.approve_skill_verification(
            verification_id, user, data.get('notes')
        )
        
        if verification:
            return api_response(
                verification.to_dict(include_skill=True, include_volunteer=True),
                'Skill verification approved successfully'
            )
        else:
            return api_response(error='Failed to approve skill verification', status=400)
            
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/admin/skill-verifications/<int:verification_id>/reject', methods=['POST'])
@jwt_required()
def reject_skill_verification(verification_id):
    """Reject skill verification (admin only)."""
    try:
        role_check = require_role('admin')
        if role_check:
            return role_check
        
        user = get_current_user()
        data = request.get_json() or {}
        
        verification = AdminService.reject_skill_verification(
            verification_id, user, data.get('notes')
        )
        
        if verification:
            return api_response(
                verification.to_dict(include_skill=True, include_volunteer=True),
                'Skill verification rejected successfully'
            )
        else:
            return api_response(error='Failed to reject skill verification', status=400)
            
    except Exception as e:
        return api_response(error=str(e), status=500)

# ============================================================================
# SYSTEM API
# ============================================================================

@bp.route('/system/health', methods=['GET'])
def health_check():
    """System health check."""
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        
        return api_response({
            'status': 'healthy',
            'database': 'connected',
            'version': '1.0.0'
        })
        
    except Exception as e:
        return api_response(error=f'System unhealthy: {str(e)}', status=500)

@bp.route('/system/stats', methods=['GET'])
@jwt_required()
def get_system_stats():
    """Get system statistics."""
    try:
        role_check = require_role('admin')
        if role_check:
            return role_check
        
        stats = {
            'total_users': User.query.count(),
            'total_volunteers': User.query.filter_by(role='volunteer').count(),
            'total_authorities': User.query.filter_by(role='authority').count(),
            'total_emergencies': EmergencyRequest.query.count(),
            'open_emergencies': EmergencyRequest.query.filter_by(status='open').count(),
            'total_assignments': Assignment.query.count(),
            'pending_verifications': VolunteerSkill.query.filter_by(verification_status='pending').count()
        }
        
        return api_response(stats)
        
    except Exception as e:
        return api_response(error=str(e), status=500)

# ============================================================================
# VOLUNTEER INTERESTS AND CERTIFICATIONS API
# ============================================================================

@bp.route('/volunteers/interests', methods=['GET'])
@jwt_required()
def get_volunteer_interests():
    """Get volunteer interests."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        interests = user.volunteer_profile.interests_list
        
        return api_response({'interests': interests})
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/interests', methods=['PUT'])
@jwt_required()
def update_volunteer_interests():
    """Update volunteer interests."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        interests = data.get('interests', [])
        if not isinstance(interests, list):
            return api_response(error='Interests must be a list', status=400)
        
        user.volunteer_profile.set_interests(interests)
        db.session.commit()
        
        return api_response(message='Interests updated successfully')
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/languages', methods=['GET'])
@jwt_required()
def get_volunteer_languages():
    """Get volunteer languages."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        languages = user.volunteer_profile.languages_list
        
        return api_response({'languages': languages})
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/languages', methods=['PUT'])
@jwt_required()
def update_volunteer_languages():
    """Update volunteer languages."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        languages = data.get('languages', [])
        if not isinstance(languages, list):
            return api_response(error='Languages must be a list', status=400)
        
        user.volunteer_profile.set_languages(languages)
        db.session.commit()
        
        return api_response(message='Languages updated successfully')
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/experience', methods=['PUT'])
@jwt_required()
def update_volunteer_experience():
    """Update volunteer experience level."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        experience_level = data.get('experience_level')
        if experience_level not in ['beginner', 'intermediate', 'advanced', 'expert']:
            return api_response(error='Invalid experience level', status=400)
        
        user.volunteer_profile.experience_level = experience_level
        db.session.commit()
        
        return api_response(message='Experience level updated successfully')
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/emergency-contact', methods=['PUT'])
@jwt_required()
def update_emergency_contact():
    """Update volunteer emergency contact."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        user.volunteer_profile.emergency_contact_name = data.get('name')
        user.volunteer_profile.emergency_contact_phone = data.get('phone')
        db.session.commit()
        
        return api_response(message='Emergency contact updated successfully')
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/nearby-emergencies', methods=['GET'])
@jwt_required()
def get_nearby_emergencies():
    """Get nearby emergencies for volunteer."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        radius = request.args.get('radius', 25, type=int)
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        from app.volunteer.services import VolunteerService
        emergencies = VolunteerService.get_nearby_emergencies(user, radius)
        
        return api_response({
            'emergencies': [
                e[0].to_dict(include_authority=True, include_skills=True) if isinstance(e, tuple) 
                else e.to_dict(include_authority=True, include_skills=True)
                for e in emergencies
            ],
            'radius_km': radius
        })
        
    except Exception as e:
        return api_response(error=str(e), status=500)

@bp.route('/volunteers/stats', methods=['GET'])
@jwt_required()
def get_volunteer_stats():
    """Get volunteer statistics."""
    try:
        role_check = require_role('volunteer')
        if role_check:
            return role_check
            
        user = get_current_user()
        
        if not user or not user.volunteer_profile:
            return api_response(error='Volunteer profile not found', status=404)
        
        from app.volunteer.services import VolunteerService
        stats = VolunteerService.get_volunteer_stats(user)
        
        return api_response({'stats': stats})
        
    except Exception as e:
        return api_response(error=str(e), status=500)

# ============================================================================
# AUTHORITY ENHANCED API
# ============================================================================

@bp.route('/emergencies/<int:emergency_id>/update', methods=['PUT'])
@jwt_required()
def update_emergency(emergency_id):
    """Update emergency details."""
    try:
        role_check = require_role('authority')
        if role_check:
            return role_check
        
        user = get_current_user()
        data = request.get_json()
        
        emergency = EmergencyRequest.query.get(emergency_id)
        if not emergency:
            return api_response(error='Emergency not found', status=404)
        
        if emergency.authority_id != user.id:
            return api_response(error='Access denied', status=403)
        
        # Update allowed fields
        if 'incident_type' in data:
            emergency.incident_type = data['incident_type']
        if 'estimated_duration_hours' in data:
            emergency.estimated_duration_hours = data['estimated_duration_hours']
        if 'hazard_level' in data:
            if data['hazard_level'] in ['low', 'medium', 'high', 'extreme']:
                emergency.hazard_level = data['hazard_level']
        if 'weather_conditions' in data:
            emergency.weather_conditions = data['weather_conditions']
        if 'special_instructions' in data:
            emergency.special_instructions = data['special_instructions']
        if 'media_contact_allowed' in data:
            emergency.media_contact_allowed = bool(data['media_contact_allowed'])
        
        emergency.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return api_response(
            emergency.to_dict(include_authority=True, include_skills=True),
            'Emergency updated successfully'
        )
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

@bp.route('/emergencies/<int:emergency_id>/complete', methods=['POST'])
@jwt_required()
def complete_emergency(emergency_id):
    """Mark emergency as completed."""
    try:
        user = get_current_user()
        claims = get_jwt()
        
        if claims.get('role') not in ['authority', 'admin']:
            return api_response(error='Authority or admin role required', status=403)
        
        emergency = EmergencyRequest.query.get(emergency_id)
        if not emergency:
            return api_response(error='Emergency not found', status=404)
        
        if claims.get('role') == 'authority' and emergency.authority_id != user.id:
            return api_response(error='Access denied', status=403)
        
        emergency.status = 'completed'
        emergency.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return api_response(
            emergency.to_dict(include_authority=True, include_skills=True),
            'Emergency marked as completed'
        )
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

@bp.route('/emergencies/<int:emergency_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_emergency(emergency_id):
    """Cancel emergency."""
    try:
        user = get_current_user()
        claims = get_jwt()
        
        if claims.get('role') not in ['authority', 'admin']:
            return api_response(error='Authority or admin role required', status=403)
        
        emergency = EmergencyRequest.query.get(emergency_id)
        if not emergency:
            return api_response(error='Emergency not found', status=404)
        
        if claims.get('role') == 'authority' and emergency.authority_id != user.id:
            return api_response(error='Access denied', status=403)
        
        emergency.status = 'cancelled'
        emergency.updated_at = datetime.now(timezone.utc)
        
        # Cancel all pending assignments
        for assignment in emergency.assignments:
            if assignment.status == 'requested':
                assignment.status = 'cancelled'
        
        db.session.commit()
        
        return api_response(
            emergency.to_dict(include_authority=True, include_skills=True),
            'Emergency cancelled successfully'
        )
        
    except Exception as e:
        db.session.rollback()
        return api_response(error=str(e), status=500)

@bp.route('/authority/dashboard/stats', methods=['GET'])
@jwt_required()
def get_authority_dashboard_stats():
    """Get authority dashboard statistics."""
    try:
        role_check = require_role('authority')
        if role_check:
            return role_check
        
        user = get_current_user()
        
        # Get authority's emergency statistics
        total_emergencies = EmergencyRequest.query.filter_by(authority_id=user.id).count()
        open_emergencies = EmergencyRequest.query.filter_by(
            authority_id=user.id, status='open'
        ).count()
        completed_emergencies = EmergencyRequest.query.filter_by(
            authority_id=user.id, status='completed'
        ).count()
        
        # Get assignment statistics for authority's emergencies
        authority_emergency_ids = [e.id for e in EmergencyRequest.query.filter_by(
            authority_id=user.id
        ).all()]
        
        if authority_emergency_ids:
            pending_assignments = Assignment.query.filter(
                Assignment.emergency_id.in_(authority_emergency_ids),
                Assignment.status == 'requested'
            ).count()
            
            active_assignments = Assignment.query.filter(
                Assignment.emergency_id.in_(authority_emergency_ids),
                Assignment.status == 'accepted'
            ).count()
        else:
            pending_assignments = 0
            active_assignments = 0
        
        stats = {
            'total_emergencies': total_emergencies,
            'open_emergencies': open_emergencies,
            'completed_emergencies': completed_emergencies,
            'pending_assignments': pending_assignments,
            'active_assignments': active_assignments
        }
        
        return api_response({'stats': stats})
        
    except Exception as e:
        return api_response(error=str(e), status=500)