"""
Volunteer management services for the Emergency Response Platform.
"""

from flask import current_app
from app import db
from app.models import VolunteerProfile, Skill, VolunteerSkill, Assignment, ActivityLog
from app.auth.utils import log_user_activity
from sqlalchemy import and_, func
from datetime import datetime, timezone

class VolunteerService:
    """Service class for volunteer profile management."""
    
    @staticmethod
    def create_profile(user, profile_data):
        """Create a new volunteer profile."""
        try:
            # Check if profile already exists
            if user.volunteer_profile:
                raise ValueError("Volunteer profile already exists")
            
            profile = VolunteerProfile(
                user_id=user.id,
                latitude=profile_data.get('latitude'),
                longitude=profile_data.get('longitude'),
                city=profile_data.get('city'),
                availability_status=profile_data.get('availability_status', 'offline'),
                bio=profile_data.get('bio')
            )
            
            db.session.add(profile)
            db.session.commit()
            
            # Log activity
            ActivityLog.log_profile_update(
                user=user,
                profile_data=profile_data
            )
            
            return profile
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def update_profile(user, profile_data):
        """Update an existing volunteer profile."""
        try:
            profile = user.volunteer_profile
            if not profile:
                raise ValueError("Volunteer profile does not exist")
            
            # Update fields if provided
            if 'latitude' in profile_data:
                profile.latitude = profile_data['latitude']
            if 'longitude' in profile_data:
                profile.longitude = profile_data['longitude']
            if 'city' in profile_data:
                profile.city = profile_data['city']
            if 'bio' in profile_data:
                profile.bio = profile_data['bio']
            
            profile.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            
            # Log activity
            ActivityLog.log_profile_update(
                user=user,
                profile_data=profile_data
            )
            
            return profile
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def update_availability(user, status):
        """Update volunteer availability status."""
        try:
            profile = user.volunteer_profile
            if not profile:
                raise ValueError("Volunteer profile does not exist")
            
            if status not in ['available', 'busy', 'offline']:
                raise ValueError("Invalid availability status")
            
            old_status = profile.availability_status
            profile.availability_status = status
            profile.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            # Log activity
            ActivityLog.log_availability_change(
                user=user,
                old_status=old_status,
                new_status=status
            )
            
            return profile
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def add_skill(user, skill_id, documents_path=None):
        """Add a skill to volunteer profile for verification."""
        try:
            profile = user.volunteer_profile
            if not profile:
                raise ValueError("Volunteer profile does not exist")
            
            # Check if skill exists
            skill = Skill.query.get(skill_id)
            if not skill:
                raise ValueError("Skill does not exist")
            
            # Check if volunteer already has this skill
            existing_skill = VolunteerSkill.query.filter_by(
                volunteer_id=profile.id,
                skill_id=skill_id
            ).first()
            
            if existing_skill:
                raise ValueError("Volunteer already has this skill")
            
            volunteer_skill = VolunteerSkill(
                volunteer_id=profile.id,
                skill_id=skill_id,
                verification_status='pending',
                documents_path=documents_path
            )
            
            db.session.add(volunteer_skill)
            db.session.commit()
            
            # Log activity
            log_user_activity(
                action='skill_added',
                entity_type='volunteer_skill',
                entity_id=volunteer_skill.id,
                details={
                    'skill_name': skill.name,
                    'skill_category': skill.category
                }
            )
            
            return volunteer_skill
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def remove_skill(user, skill_id):
        """Remove a skill from volunteer profile."""
        try:
            profile = user.volunteer_profile
            if not profile:
                raise ValueError("Volunteer profile does not exist")
            
            volunteer_skill = VolunteerSkill.query.filter_by(
                volunteer_id=profile.id,
                skill_id=skill_id
            ).first()
            
            if not volunteer_skill:
                raise ValueError("Volunteer does not have this skill")
            
            skill_name = volunteer_skill.skill.name
            db.session.delete(volunteer_skill)
            db.session.commit()
            
            # Log activity
            log_user_activity(
                action='skill_removed',
                entity_type='volunteer_skill',
                entity_id=skill_id,
                details={'skill_name': skill_name}
            )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_volunteer_history(user, limit=None):
        """Get volunteer's assignment history."""
        profile = user.volunteer_profile
        if not profile:
            return []
        
        return Assignment.get_volunteer_history(profile.id, limit)
    
    @staticmethod
    def get_pending_assignments(user):
        """Get volunteer's pending assignments."""
        profile = user.volunteer_profile
        if not profile:
            return []
        
        return Assignment.get_pending_assignments(profile.id)
    
    @staticmethod
    def get_active_assignments(user):
        """Get volunteer's active assignments."""
        profile = user.volunteer_profile
        if not profile:
            return []
        
        return Assignment.get_active_assignments(profile.id)
    
    @staticmethod
    def respond_to_assignment(user, assignment_id, response, notes=None):
        """Respond to an assignment request."""
        try:
            profile = user.volunteer_profile
            if not profile:
                raise ValueError("Volunteer profile does not exist")
            
            assignment = Assignment.query.filter_by(
                id=assignment_id,
                volunteer_id=profile.id,
                status='requested'
            ).first()
            
            if not assignment:
                raise ValueError("Assignment not found or already responded to")
            
            if response == 'accept':
                assignment.accept(notes)
            elif response == 'decline':
                assignment.decline(notes)
            else:
                raise ValueError("Invalid response. Must be 'accept' or 'decline'")
            
            db.session.commit()
            
            # Log activity
            ActivityLog.log_assignment_response(
                user=user,
                assignment=assignment,
                response=response
            )
            
            return assignment
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def complete_assignment(user, assignment_id, notes=None):
        """Mark an assignment as completed."""
        try:
            profile = user.volunteer_profile
            if not profile:
                raise ValueError("Volunteer profile does not exist")
            
            assignment = Assignment.query.filter_by(
                id=assignment_id,
                volunteer_id=profile.id,
                status='accepted'
            ).first()
            
            if not assignment:
                raise ValueError("Assignment not found or not in accepted state")
            
            assignment.complete(notes)
            db.session.commit()
            
            # Log activity
            ActivityLog.log_assignment_completion(
                user=user,
                assignment=assignment
            )
            
            return assignment
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_nearby_emergencies(user, radius_km=None):
        """Get nearby emergency requests that match volunteer's skills."""
        profile = user.volunteer_profile
        if not profile:
            return []
        
        # Use default radius if not provided
        if radius_km is None:
            radius_km = current_app.config.get('DEFAULT_SEARCH_RADIUS_KM', 25)
        
        from app.models.emergency import EmergencyRequest, EmergencyRequiredSkill
        
        # If volunteer has no location, show all open emergencies (for now)
        if not profile.latitude or not profile.longitude:
            emergencies = EmergencyRequest.query.filter_by(status='open').order_by(
                EmergencyRequest.created_at.desc()
            ).limit(10).all()
            # Return as tuples with None distance for consistency
            return [(emergency, None) for emergency in emergencies]
        
        # Get volunteer's skills (both verified and pending for broader matching)
        skill_ids = [vs.skill_id for vs in profile.volunteer_skills]
        
        # If no skills, show all open emergencies within radius
        if not skill_ids:
            try:
                lat_rad = func.radians(float(profile.latitude))
                lon_rad = func.radians(float(profile.longitude))
                
                # Haversine distance calculation
                distance = (
                    6371 * func.acos(
                        func.cos(lat_rad) * func.cos(func.radians(EmergencyRequest.latitude)) *
                        func.cos(func.radians(EmergencyRequest.longitude) - lon_rad) +
                        func.sin(lat_rad) * func.sin(func.radians(EmergencyRequest.latitude))
                    )
                )
                
                emergencies = db.session.query(EmergencyRequest).filter(
                    and_(
                        EmergencyRequest.status == 'open',
                        EmergencyRequest.latitude.isnot(None),
                        EmergencyRequest.longitude.isnot(None),
                        distance <= radius_km
                    )
                ).add_columns(distance.label('distance')).order_by('distance').limit(10).all()
                
                return emergencies
            except (TypeError, ValueError):
                # If distance calculation fails, return all open emergencies
                emergencies = EmergencyRequest.query.filter_by(status='open').order_by(
                    EmergencyRequest.created_at.desc()
                ).limit(10).all()
                return [(emergency, None) for emergency in emergencies]
        
        # Find open emergencies within radius that require volunteer's skills
        try:
            lat_rad = func.radians(float(profile.latitude))
            lon_rad = func.radians(float(profile.longitude))
            
            # Haversine distance calculation
            distance = (
                6371 * func.acos(
                    func.cos(lat_rad) * func.cos(func.radians(EmergencyRequest.latitude)) *
                    func.cos(func.radians(EmergencyRequest.longitude) - lon_rad) +
                    func.sin(lat_rad) * func.sin(func.radians(EmergencyRequest.latitude))
                )
            )
            
            # Get emergencies that match volunteer's skills
            skill_matched_emergencies = db.session.query(EmergencyRequest).join(
                EmergencyRequiredSkill
            ).filter(
                and_(
                    EmergencyRequest.status == 'open',
                    EmergencyRequest.latitude.isnot(None),
                    EmergencyRequest.longitude.isnot(None),
                    EmergencyRequiredSkill.skill_id.in_(skill_ids),
                    distance <= radius_km
                )
            ).add_columns(distance.label('distance')).order_by('distance').distinct().all()
            
            # If no skill-matched emergencies, show all open emergencies within radius
            if not skill_matched_emergencies:
                all_emergencies = db.session.query(EmergencyRequest).filter(
                    and_(
                        EmergencyRequest.status == 'open',
                        EmergencyRequest.latitude.isnot(None),
                        EmergencyRequest.longitude.isnot(None),
                        distance <= radius_km
                    )
                ).add_columns(distance.label('distance')).order_by('distance').limit(10).all()
                
                return all_emergencies
            
            return skill_matched_emergencies
            
        except (TypeError, ValueError):
            # If distance calculation fails, return all open emergencies
            emergencies = EmergencyRequest.query.filter_by(status='open').order_by(
                EmergencyRequest.created_at.desc()
            ).limit(10).all()
            return [(emergency, None) for emergency in emergencies]
    
    @staticmethod
    def get_volunteer_stats(user):
        """Get volunteer statistics."""
        profile = user.volunteer_profile
        if not profile:
            return {
                'total_assignments': 0,
                'completed_assignments': 0,
                'pending_assignments': 0,
                'active_assignments': 0,
                'verified_skills': 0,
                'pending_skills': 0,
                'rejected_skills': 0
            }
        
        try:
            assignments = Assignment.query.filter_by(volunteer_id=profile.id).all()
            
            # Safely get skill counts
            verified_skills = getattr(profile, 'verified_skills', [])
            pending_skills = getattr(profile, 'pending_skills', [])
            rejected_skills = getattr(profile, 'rejected_skills', [])
            
            return {
                'total_assignments': len(assignments),
                'completed_assignments': len([a for a in assignments if hasattr(a, 'is_completed') and a.is_completed]),
                'pending_assignments': len([a for a in assignments if hasattr(a, 'is_requested') and a.is_requested]),
                'active_assignments': len([a for a in assignments if hasattr(a, 'is_accepted') and a.is_accepted]),
                'verified_skills': len(verified_skills),
                'pending_skills': len(pending_skills),
                'rejected_skills': len(rejected_skills)
            }
        except Exception as e:
            # Return safe defaults if there's any error
            return {
                'total_assignments': 0,
                'completed_assignments': 0,
                'pending_assignments': 0,
                'active_assignments': 0,
                'verified_skills': 0,
                'pending_skills': 0,
                'rejected_skills': 0
            }
    
    @staticmethod
    def get_all_open_emergencies():
        """Get all open emergency requests for testing/debugging."""
        from app.models.emergency import EmergencyRequest
        return EmergencyRequest.query.filter_by(status='open').order_by(
            EmergencyRequest.created_at.desc()
        ).all()

class SkillService:
    """Service class for skill management."""
    
    @staticmethod
    def get_all_skills():
        """Get all available skills."""
        return Skill.query.order_by(Skill.category, Skill.name).all()
    
    @staticmethod
    def get_skills_by_category(category):
        """Get skills by category."""
        return Skill.get_by_category(category)
    
    @staticmethod
    def search_skills(query):
        """Search skills by name."""
        return Skill.search_by_name(query)
    
    @staticmethod
    def create_skill(name, category, description=None):
        """Create a new skill."""
        try:
            # Check if skill already exists
            existing_skill = Skill.query.filter_by(name=name).first()
            if existing_skill:
                raise ValueError("Skill already exists")
            
            skill = Skill(
                name=name,
                category=category,
                description=description
            )
            
            db.session.add(skill)
            db.session.commit()
            
            return skill
            
        except Exception as e:
            db.session.rollback()
            raise e