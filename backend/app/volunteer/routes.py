"""
Volunteer routes for the Emergency Response Platform.
"""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user, login_required
from app import db
from app.volunteer import bp
from app.volunteer.services import VolunteerService, SkillService
from app.volunteer.forms import VolunteerProfileForm, AddSkillForm, AssignmentResponseForm, CompleteAssignmentForm, AvailabilityForm
from app.auth.utils import require_volunteer, log_user_activity
from app.models import Skill, Assignment

@bp.route('/dashboard')
@login_required
@require_volunteer()
def dashboard():
    """Volunteer dashboard."""
    try:
        # Get volunteer statistics
        stats = VolunteerService.get_volunteer_stats(current_user)
        
        # Get pending assignments
        pending_assignments = VolunteerService.get_pending_assignments(current_user)
        
        # Get active assignments
        active_assignments = VolunteerService.get_active_assignments(current_user)
        
        # Get recent assignment history
        recent_history = VolunteerService.get_volunteer_history(current_user, limit=5)
        
        # Get nearby emergencies
        nearby_emergencies = VolunteerService.get_nearby_emergencies(current_user)
        
        # If no nearby emergencies, show all open emergencies for now
        if not nearby_emergencies:
            all_open = VolunteerService.get_all_open_emergencies()
            nearby_emergencies = [(emergency, None) for emergency in all_open[:5]]
        
        return render_template('volunteer/dashboard.html',
                             stats=stats,
                             pending_assignments=pending_assignments or [],
                             active_assignments=active_assignments or [],
                             recent_history=recent_history or [],
                             nearby_emergencies=nearby_emergencies or [])
    except Exception as e:
        # Log the error and show a safe dashboard
        print(f"Error loading volunteer dashboard: {str(e)}")
        return render_template('volunteer/dashboard.html',
                             stats={
                                 'total_assignments': 0,
                                 'completed_assignments': 0,
                                 'pending_assignments': 0,
                                 'active_assignments': 0,
                                 'verified_skills': 0,
                                 'pending_skills': 0,
                                 'rejected_skills': 0
                             },
                             pending_assignments=[],
                             active_assignments=[],
                             recent_history=[],
                             nearby_emergencies=[])

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
@require_volunteer()
def profile():
    """Volunteer profile management."""
    form = VolunteerProfileForm()
    profile = current_user.volunteer_profile
    
    # Pre-populate form with current data
    if request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
        form.phone.data = current_user.phone
        
        if profile:
            form.city.data = profile.city
            form.availability_status.data = profile.availability_status
            form.bio.data = profile.bio
            form.latitude.data = profile.latitude
            form.longitude.data = profile.longitude
    
    if form.validate_on_submit():
        try:
            # Update user info
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.phone = form.phone.data
            
            profile_data = {
                'city': form.city.data,
                'bio': form.bio.data,
                'latitude': float(form.latitude.data) if form.latitude.data else None,
                'longitude': float(form.longitude.data) if form.longitude.data else None
            }
            
            if profile:
                # Update availability status
                VolunteerService.update_availability(current_user, form.availability_status.data)
                VolunteerService.update_profile(current_user, profile_data)
                flash('Profile updated successfully!', 'success')
            else:
                profile_data['availability_status'] = form.availability_status.data
                VolunteerService.create_profile(current_user, profile_data)
                flash('Profile created successfully!', 'success')
            
            db.session.commit()
            return redirect(url_for('volunteer.profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')
    
    # Get all skills for the skills section
    all_skills = SkillService.get_all_skills()
    skills_by_category = {}
    for skill in all_skills:
        if skill.category not in skills_by_category:
            skills_by_category[skill.category] = []
        skills_by_category[skill.category].append(skill)
    
    return render_template('volunteer/profile.html',
                         form=form,
                         profile=profile,
                         skills_by_category=skills_by_category)

@bp.route('/availability', methods=['POST'])
@login_required
@require_volunteer()
def update_availability():
    """Update volunteer availability status."""
    try:
        status = request.form.get('status') or request.json.get('status')
        
        if not status or status not in ['available', 'busy', 'offline']:
            if request.is_json:
                return jsonify({'error': 'Invalid availability status'}), 400
            flash('Invalid availability status', 'error')
            return redirect(url_for('volunteer.dashboard'))
        
        VolunteerService.update_availability(current_user, status)
        
        if request.is_json:
            return jsonify({
                'message': 'Availability updated successfully',
                'status': status
            })
        
        flash(f'Availability updated to {status.title()}', 'success')
        return redirect(url_for('volunteer.dashboard'))
        
    except Exception as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 500
        flash(f'Error updating availability: {str(e)}', 'error')
        return redirect(url_for('volunteer.dashboard'))

@bp.route('/skills')
@login_required
@require_volunteer()
def skills():
    """Manage volunteer skills."""
    # Get all skills for the add skill form
    all_skills = SkillService.get_all_skills()
    skills_by_category = {}
    for skill in all_skills:
        if skill.category not in skills_by_category:
            skills_by_category[skill.category] = []
        skills_by_category[skill.category].append(skill)
    
    return render_template('volunteer/skills.html',
                         skills_by_category=skills_by_category)

@bp.route('/skills/add', methods=['POST'])
@login_required
@require_volunteer()
def add_skill():
    """Add a skill to volunteer profile."""
    try:
        skill_id = int(request.form.get('skill_id') or request.json.get('skill_id'))
        
        VolunteerService.add_skill(current_user, skill_id)
        
        if request.is_json:
            return jsonify({'message': 'Skill added successfully'})
        
        flash('Skill added for verification', 'success')
        return redirect(url_for('volunteer.profile'))
        
    except ValueError as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('volunteer.profile'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': 'Failed to add skill'}), 500
        flash(f'Error adding skill: {str(e)}', 'error')
        return redirect(url_for('volunteer.profile'))

@bp.route('/skills/remove/<int:skill_id>', methods=['POST'])
@login_required
@require_volunteer()
def remove_skill(skill_id):
    """Remove a skill from volunteer profile."""
    try:
        VolunteerService.remove_skill(current_user, skill_id)
        
        if request.is_json:
            return jsonify({'message': 'Skill removed successfully'})
        
        flash('Skill removed from profile', 'success')
        return redirect(url_for('volunteer.profile'))
        
    except ValueError as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('volunteer.profile'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': 'Failed to remove skill'}), 500
        flash(f'Error removing skill: {str(e)}', 'error')
        return redirect(url_for('volunteer.profile'))

@bp.route('/assignments/<int:assignment_id>/respond', methods=['POST'])
@login_required
@require_volunteer()
def respond_to_assignment(assignment_id):
    """Respond to an assignment request."""
    try:
        response = request.form.get('response') or request.json.get('response')
        notes = request.form.get('notes') or request.json.get('notes', '')
        
        if response not in ['accept', 'decline']:
            if request.is_json:
                return jsonify({'error': 'Invalid response. Must be accept or decline'}), 400
            flash('Invalid response', 'error')
            return redirect(url_for('volunteer.dashboard'))
        
        assignment = VolunteerService.respond_to_assignment(
            current_user, assignment_id, response, notes
        )
        
        if request.is_json:
            return jsonify({
                'message': f'Assignment {response}ed successfully',
                'assignment': assignment.to_dict(include_emergency=True)
            })
        
        flash(f'Assignment {response}ed successfully', 'success')
        return redirect(url_for('volunteer.dashboard'))
        
    except ValueError as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('volunteer.dashboard'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': 'Failed to respond to assignment'}), 500
        flash(f'Error responding to assignment: {str(e)}', 'error')
        return redirect(url_for('volunteer.dashboard'))

@bp.route('/assignments/<int:assignment_id>/complete', methods=['POST'])
@login_required
@require_volunteer()
def complete_assignment(assignment_id):
    """Mark an assignment as completed."""
    try:
        notes = request.form.get('notes') or request.json.get('notes', '')
        
        assignment = VolunteerService.complete_assignment(
            current_user, assignment_id, notes
        )
        
        if request.is_json:
            return jsonify({
                'message': 'Assignment completed successfully',
                'assignment': assignment.to_dict(include_emergency=True)
            })
        
        flash('Assignment marked as completed', 'success')
        return redirect(url_for('volunteer.dashboard'))
        
    except ValueError as e:
        if request.is_json:
            return jsonify({'error': str(e)}), 400
        flash(str(e), 'error')
        return redirect(url_for('volunteer.dashboard'))
    except Exception as e:
        if request.is_json:
            return jsonify({'error': 'Failed to complete assignment'}), 500
        flash(f'Error completing assignment: {str(e)}', 'error')
        return redirect(url_for('volunteer.dashboard'))

@bp.route('/history')
@login_required
@require_volunteer()
def history():
    """View volunteer assignment history."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get all volunteer history
    all_history = VolunteerService.get_volunteer_history(current_user)
    
    # Simple pagination
    start = (page - 1) * per_page
    end = start + per_page
    history_page = all_history[start:end]
    
    has_prev = page > 1
    has_next = end < len(all_history)
    
    return render_template('volunteer/history.html',
                         assignments=history_page,
                         page=page,
                         has_prev=has_prev,
                         has_next=has_next,
                         total=len(all_history))

@bp.route('/emergencies/nearby')
@login_required
@require_volunteer()
def nearby_emergencies():
    """View nearby emergency requests."""
    radius = request.args.get('radius', 25, type=int)
    
    emergencies = VolunteerService.get_nearby_emergencies(current_user, radius)
    
    if request.is_json:
        return jsonify({
            'emergencies': [e[0].to_dict(include_authority=True, include_skills=True) 
                          for e in emergencies],
            'radius_km': radius
        })
    
    return render_template('volunteer/nearby_emergencies.html',
                         emergencies=emergencies,
                         radius=radius)

# API endpoints
@bp.route('/api/profile', methods=['GET'])
@login_required
@require_volunteer()
def api_get_profile():
    """Get volunteer profile via API."""
    profile = current_user.volunteer_profile
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    return jsonify({
        'profile': profile.to_dict(include_user=True),
        'stats': VolunteerService.get_volunteer_stats(current_user)
    })

@bp.route('/api/profile', methods=['PUT'])
@login_required
@require_volunteer()
def api_update_profile():
    """Update volunteer profile via API."""
    try:
        data = request.get_json()
        
        profile_data = {}
        if 'latitude' in data:
            profile_data['latitude'] = float(data['latitude']) if data['latitude'] else None
        if 'longitude' in data:
            profile_data['longitude'] = float(data['longitude']) if data['longitude'] else None
        if 'city' in data:
            profile_data['city'] = data['city']
        if 'bio' in data:
            profile_data['bio'] = data['bio']
        
        if current_user.volunteer_profile:
            profile = VolunteerService.update_profile(current_user, profile_data)
        else:
            profile = VolunteerService.create_profile(current_user, profile_data)
        
        return jsonify({
            'message': 'Profile updated successfully',
            'profile': profile.to_dict(include_user=True)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/assignments', methods=['GET'])
@login_required
@require_volunteer()
def api_get_assignments():
    """Get volunteer assignments via API."""
    assignment_type = request.args.get('type', 'all')
    
    if assignment_type == 'pending':
        assignments = VolunteerService.get_pending_assignments(current_user)
    elif assignment_type == 'active':
        assignments = VolunteerService.get_active_assignments(current_user)
    else:
        assignments = VolunteerService.get_volunteer_history(current_user, limit=50)
    
    return jsonify({
        'assignments': [a.to_dict(include_emergency=True) for a in assignments],
        'type': assignment_type
    })

@bp.route('/api/stats', methods=['GET'])
@login_required
@require_volunteer()
def api_get_stats():
    """Get volunteer statistics via API."""
    stats = VolunteerService.get_volunteer_stats(current_user)
    return jsonify({'stats': stats})

@bp.route('/api/debug/emergencies', methods=['GET'])
@login_required
def api_debug_emergencies():
    """Debug endpoint to see all open emergencies."""
    emergencies = VolunteerService.get_all_open_emergencies()
    return jsonify({
        'total_open_emergencies': len(emergencies),
        'emergencies': [e.to_dict(include_authority=True) for e in emergencies]
    })

@bp.route('/test-emergencies')
@login_required
@require_volunteer()
def test_emergencies():
    """Test page to show all emergencies."""
    try:
        all_emergencies = VolunteerService.get_all_open_emergencies()
        nearby_emergencies = VolunteerService.get_nearby_emergencies(current_user)
        
        return f"""
        <h1>Emergency Test Page</h1>
        <h2>All Open Emergencies ({len(all_emergencies)})</h2>
        <ul>
        {''.join([f'<li>{e.title} - {e.status} - Created by: {e.authority.first_name} {e.authority.last_name}</li>' for e in all_emergencies])}
        </ul>
        
        <h2>Nearby Emergencies for Current User ({len(nearby_emergencies)})</h2>
        <ul>
        {''.join([f'<li>{e[0].title if isinstance(e, tuple) else e.title} - Distance: {e[1] if isinstance(e, tuple) and e[1] else "N/A"}</li>' for e in nearby_emergencies])}
        </ul>
        
        <h2>User Profile Info</h2>
        <p>User: {current_user.first_name} {current_user.last_name}</p>
        <p>Profile exists: {current_user.volunteer_profile is not None}</p>
        {f'<p>Location: {current_user.volunteer_profile.latitude}, {current_user.volunteer_profile.longitude}</p>' if current_user.volunteer_profile else '<p>No location set</p>'}
        {f'<p>Skills: {len(current_user.volunteer_profile.volunteer_skills)}</p>' if current_user.volunteer_profile else '<p>No skills</p>'}
        
        <p><a href="/volunteer/dashboard">Back to Dashboard</a></p>
        """
    except Exception as e:
        return f"Error: {str(e)}"