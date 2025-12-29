"""
Volunteer API endpoints.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.api import bp
from app.models import User, VolunteerProfile, Skill, VolunteerSkill, Assignment
from app import db
from app.volunteer.services import VolunteerService

def require_volunteer():
    """Decorator to require volunteer role."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            if claims.get('role') != 'volunteer':
                return jsonify({'error': 'Volunteer role required'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

@bp.route('/volunteers/profile', methods=['GET'])
@jwt_required()
@require_volunteer()
def get_volunteer_profile():
    """Get volunteer profile."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.volunteer_profile:
            return jsonify({'error': 'Volunteer profile not found'}), 404
        
        profile_data = user.volunteer_profile.to_dict(include_user=True)
        profile_data['skills'] = [
            vs.to_dict(include_skill=True) for vs in user.volunteer_profile.volunteer_skills
        ]
        
        return jsonify({'profile': profile_data}), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get profile', 'details': str(e)}), 500

@bp.route('/volunteers/profile', methods=['POST', 'PUT'])
@jwt_required()
@require_volunteer()
def update_volunteer_profile():
    """Create or update volunteer profile."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Update or create profile
        success = VolunteerService.update_profile(user, data)
        
        if success:
            return jsonify({'message': 'Profile updated successfully'}), 200
        else:
            return jsonify({'error': 'Failed to update profile'}), 400
            
    except Exception as e:
        return jsonify({'error': 'Profile update failed', 'details': str(e)}), 500

@bp.route('/volunteers/availability', methods=['PUT'])
@jwt_required()
@require_volunteer()
def update_availability():
    """Update volunteer availability status."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return jsonify({'error': 'Volunteer profile not found'}), 404
        
        status = data.get('status')
        if status not in ['available', 'busy', 'offline']:
            return jsonify({'error': 'Invalid availability status'}), 400
        
        success = VolunteerService.update_availability(user, status)
        
        if success:
            return jsonify({'message': 'Availability updated successfully'}), 200
        else:
            return jsonify({'error': 'Failed to update availability'}), 400
            
    except Exception as e:
        return jsonify({'error': 'Availability update failed', 'details': str(e)}), 500

@bp.route('/volunteers/skills', methods=['GET'])
@jwt_required()
@require_volunteer()
def get_volunteer_skills():
    """Get volunteer skills."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.volunteer_profile:
            return jsonify({'error': 'Volunteer profile not found'}), 404
        
        skills = [
            vs.to_dict(include_skill=True) 
            for vs in user.volunteer_profile.volunteer_skills
        ]
        
        return jsonify({'skills': skills}), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get skills', 'details': str(e)}), 500

@bp.route('/volunteers/skills', methods=['POST'])
@jwt_required()
@require_volunteer()
def add_volunteer_skill():
    """Add a skill to volunteer profile."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return jsonify({'error': 'Volunteer profile not found'}), 404
        
        skill_id = data.get('skill_id')
        if not skill_id:
            return jsonify({'error': 'skill_id is required'}), 400
        
        # Check if skill exists
        skill = Skill.query.get(skill_id)
        if not skill:
            return jsonify({'error': 'Skill not found'}), 404
        
        # Check if already added
        existing = VolunteerSkill.query.filter_by(
            volunteer_id=user.volunteer_profile.id,
            skill_id=skill_id
        ).first()
        
        if existing:
            return jsonify({'error': 'Skill already added'}), 409
        
        # Add skill
        volunteer_skill = VolunteerSkill(
            volunteer_id=user.volunteer_profile.id,
            skill_id=skill_id,
            verification_status='pending'
        )
        
        db.session.add(volunteer_skill)
        db.session.commit()
        
        return jsonify({
            'message': 'Skill added successfully',
            'skill': volunteer_skill.to_dict(include_skill=True)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to add skill', 'details': str(e)}), 500

@bp.route('/volunteers/assignments', methods=['GET'])
@jwt_required()
@require_volunteer()
def get_volunteer_assignments():
    """Get volunteer assignments."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.volunteer_profile:
            return jsonify({'error': 'Volunteer profile not found'}), 404
        
        status_filter = request.args.get('status')
        
        query = Assignment.query.filter_by(volunteer_id=user.volunteer_profile.id)
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        assignments = query.order_by(Assignment.assigned_at.desc()).all()
        
        return jsonify({
            'assignments': [
                assignment.to_dict(include_emergency=True) 
                for assignment in assignments
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get assignments', 'details': str(e)}), 500

@bp.route('/volunteers/assignments/<int:assignment_id>/respond', methods=['PUT'])
@jwt_required()
@require_volunteer()
def respond_to_assignment(assignment_id):
    """Accept or decline an assignment."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return jsonify({'error': 'Volunteer profile not found'}), 404
        
        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        if assignment.volunteer_id != user.volunteer_profile.id:
            return jsonify({'error': 'Access denied'}), 403
        
        response = data.get('response')
        if response not in ['accepted', 'declined']:
            return jsonify({'error': 'Invalid response. Must be "accepted" or "declined"'}), 400
        
        notes = data.get('notes')
        
        if response == 'accepted':
            assignment.accept(notes)
        else:
            assignment.decline(notes)
        
        db.session.commit()
        
        return jsonify({
            'message': f'Assignment {response} successfully',
            'assignment': assignment.to_dict(include_emergency=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to respond to assignment', 'details': str(e)}), 500

@bp.route('/volunteers/assignments/<int:assignment_id>/complete', methods=['PUT'])
@jwt_required()
@require_volunteer()
def complete_assignment(assignment_id):
    """Mark assignment as completed."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not user or not user.volunteer_profile:
            return jsonify({'error': 'Volunteer profile not found'}), 404
        
        assignment = Assignment.query.get(assignment_id)
        if not assignment:
            return jsonify({'error': 'Assignment not found'}), 404
        
        if assignment.volunteer_id != user.volunteer_profile.id:
            return jsonify({'error': 'Access denied'}), 403
        
        if assignment.status != 'accepted':
            return jsonify({'error': 'Can only complete accepted assignments'}), 400
        
        notes = data.get('notes')
        assignment.complete(notes)
        db.session.commit()
        
        return jsonify({
            'message': 'Assignment completed successfully',
            'assignment': assignment.to_dict(include_emergency=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to complete assignment', 'details': str(e)}), 500