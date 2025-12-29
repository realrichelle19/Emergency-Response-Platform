"""
Volunteer matching service for the Emergency Response Platform.

This module provides intelligent matching between volunteers and emergency requests
based on location, skills, availability, and priority levels.
"""

from typing import List, Dict, Tuple, Optional
from flask import current_app
from app import db
from app.models import VolunteerProfile, EmergencyRequest, VolunteerSkill, Assignment
from app.services.location_service import LocationService
from datetime import datetime, timedelta

class MatchingService:
    """Service class for volunteer-emergency matching operations."""
    
    @staticmethod
    def find_matching_volunteers(emergency: EmergencyRequest, 
                               limit: Optional[int] = None) -> List[Dict]:
        """
        Find volunteers that match an emergency request's requirements.
        
        Args:
            emergency: The emergency request
            limit: Maximum number of volunteers to return
            
        Returns:
            List of volunteer match dictionaries with scores and details
        """
        # Get required skill IDs
        required_skill_ids = [rs.skill_id for rs in emergency.required_skills]
        mandatory_skill_ids = [rs.skill_id for rs in emergency.required_skills if rs.is_mandatory]
        optional_skill_ids = [rs.skill_id for rs in emergency.required_skills if not rs.is_mandatory]
        
        # Find volunteers in radius with required skills
        volunteers_with_distance = LocationService.find_volunteers_in_radius(
            center_lat=float(emergency.latitude),
            center_lon=float(emergency.longitude),
            radius_km=emergency.search_radius_km,
            required_skill_ids=required_skill_ids if required_skill_ids else None,
            availability_filter='available'
        )
        
        # Score and rank volunteers
        volunteer_matches = []
        for volunteer, distance in volunteers_with_distance:
            # Skip volunteers who already have assignments for this emergency
            existing_assignment = Assignment.query.filter_by(
                emergency_id=emergency.id,
                volunteer_id=volunteer.id
            ).first()
            
            if existing_assignment:
                continue
            
            match_score = MatchingService._calculate_match_score(
                volunteer, emergency, distance, mandatory_skill_ids, optional_skill_ids
            )
            
            volunteer_matches.append({
                'volunteer': volunteer,
                'distance_km': distance,
                'match_score': match_score,
                'skill_match': MatchingService._get_skill_match_details(
                    volunteer, mandatory_skill_ids, optional_skill_ids
                )
            })
        
        # Sort by match score (highest first)
        volunteer_matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        if limit:
            volunteer_matches = volunteer_matches[:limit]
        
        return volunteer_matches
    
    @staticmethod
    def _calculate_match_score(volunteer: VolunteerProfile, emergency: EmergencyRequest,
                             distance: float, mandatory_skill_ids: List[int],
                             optional_skill_ids: List[int]) -> float:
        """
        Calculate a match score for a volunteer-emergency pair.
        
        Score components:
        - Distance (closer is better): 0-40 points
        - Skill match (more skills is better): 0-40 points
        - Priority bonus (critical emergencies get boost): 0-20 points
        
        Args:
            volunteer: The volunteer profile
            emergency: The emergency request
            distance: Distance in kilometers
            mandatory_skill_ids: List of mandatory skill IDs
            optional_skill_ids: List of optional skill IDs
            
        Returns:
            Match score (0-100)
        """
        score = 0.0
        
        # Distance score (0-40 points, closer is better)
        max_distance = emergency.search_radius_km
        if max_distance > 0:
            distance_score = max(0, 40 * (1 - distance / max_distance))
            score += distance_score
        
        # Skill match score (0-40 points)
        volunteer_skill_ids = [vs.skill_id for vs in volunteer.verified_skills]
        
        # Mandatory skills (must have all for any points)
        if mandatory_skill_ids:
            mandatory_matches = sum(1 for skill_id in mandatory_skill_ids 
                                  if skill_id in volunteer_skill_ids)
            if mandatory_matches == len(mandatory_skill_ids):
                score += 25  # Base score for having all mandatory skills
            else:
                # Penalty for missing mandatory skills
                score -= 20
        
        # Optional skills (bonus points for each match)
        if optional_skill_ids:
            optional_matches = sum(1 for skill_id in optional_skill_ids 
                                 if skill_id in volunteer_skill_ids)
            optional_score = min(15, (optional_matches / len(optional_skill_ids)) * 15)
            score += optional_score
        
        # Priority bonus (0-20 points for critical emergencies)
        priority_bonuses = {
            'critical': 20,
            'high': 10,
            'medium': 5,
            'low': 0
        }
        score += priority_bonuses.get(emergency.priority_level, 0)
        
        # Ensure score is within bounds
        return max(0, min(100, score))
    
    @staticmethod
    def _get_skill_match_details(volunteer: VolunteerProfile, 
                               mandatory_skill_ids: List[int],
                               optional_skill_ids: List[int]) -> Dict:
        """
        Get detailed skill match information for a volunteer.
        
        Args:
            volunteer: The volunteer profile
            mandatory_skill_ids: List of mandatory skill IDs
            optional_skill_ids: List of optional skill IDs
            
        Returns:
            Dictionary with skill match details
        """
        volunteer_skill_ids = [vs.skill_id for vs in volunteer.verified_skills]
        
        mandatory_matches = [skill_id for skill_id in mandatory_skill_ids 
                           if skill_id in volunteer_skill_ids]
        mandatory_missing = [skill_id for skill_id in mandatory_skill_ids 
                           if skill_id not in volunteer_skill_ids]
        
        optional_matches = [skill_id for skill_id in optional_skill_ids 
                          if skill_id in volunteer_skill_ids]
        
        return {
            'mandatory_matches': len(mandatory_matches),
            'mandatory_total': len(mandatory_skill_ids),
            'mandatory_missing': len(mandatory_missing),
            'optional_matches': len(optional_matches),
            'optional_total': len(optional_skill_ids),
            'has_all_mandatory': len(mandatory_missing) == 0
        }
    
    @staticmethod
    def find_emergencies_for_volunteer(volunteer: VolunteerProfile,
                                     radius_km: Optional[int] = None) -> List[Dict]:
        """
        Find emergency requests that match a volunteer's skills and location.
        
        Args:
            volunteer: The volunteer profile
            radius_km: Search radius in kilometers
            
        Returns:
            List of emergency match dictionaries with scores and details
        """
        if not volunteer.is_available:
            return []
        
        # Get volunteer's verified skills
        volunteer_skill_ids = [vs.skill_id for vs in volunteer.verified_skills]
        if not volunteer_skill_ids:
            return []
        
        # Find nearby emergencies
        emergencies_with_distance = LocationService.find_emergencies_near_volunteer(
            volunteer, radius_km
        )
        
        # Score and rank emergencies
        emergency_matches = []
        for emergency, distance in emergencies_with_distance:
            # Skip if volunteer already has assignment for this emergency
            existing_assignment = Assignment.query.filter_by(
                emergency_id=emergency.id,
                volunteer_id=volunteer.id
            ).first()
            
            if existing_assignment:
                continue
            
            # Check if volunteer has any required skills
            required_skill_ids = [rs.skill_id for rs in emergency.required_skills]
            if required_skill_ids:
                skill_matches = [skill_id for skill_id in required_skill_ids 
                               if skill_id in volunteer_skill_ids]
                if not skill_matches:
                    continue  # Skip if no skill match
            
            match_score = MatchingService._calculate_emergency_match_score(
                volunteer, emergency, distance, volunteer_skill_ids
            )
            
            emergency_matches.append({
                'emergency': emergency,
                'distance_km': distance,
                'match_score': match_score,
                'skill_match': MatchingService._get_emergency_skill_match_details(
                    emergency, volunteer_skill_ids
                )
            })
        
        # Sort by match score (highest first)
        emergency_matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        return emergency_matches
    
    @staticmethod
    def _calculate_emergency_match_score(volunteer: VolunteerProfile, emergency: EmergencyRequest,
                                       distance: float, volunteer_skill_ids: List[int]) -> float:
        """
        Calculate a match score for an emergency-volunteer pair (from volunteer's perspective).
        
        Args:
            volunteer: The volunteer profile
            emergency: The emergency request
            distance: Distance in kilometers
            volunteer_skill_ids: List of volunteer's verified skill IDs
            
        Returns:
            Match score (0-100)
        """
        score = 0.0
        
        # Distance score (0-30 points, closer is better)
        max_distance = emergency.search_radius_km
        if max_distance > 0:
            distance_score = max(0, 30 * (1 - distance / max_distance))
            score += distance_score
        
        # Priority score (0-40 points, higher priority is better)
        priority_scores = {
            'critical': 40,
            'high': 30,
            'medium': 20,
            'low': 10
        }
        score += priority_scores.get(emergency.priority_level, 0)
        
        # Skill relevance score (0-30 points)
        required_skill_ids = [rs.skill_id for rs in emergency.required_skills]
        if required_skill_ids:
            skill_matches = sum(1 for skill_id in required_skill_ids 
                              if skill_id in volunteer_skill_ids)
            skill_score = (skill_matches / len(required_skill_ids)) * 30
            score += skill_score
        else:
            score += 15  # Base score if no specific skills required
        
        # Ensure score is within bounds
        return max(0, min(100, score))
    
    @staticmethod
    def _get_emergency_skill_match_details(emergency: EmergencyRequest,
                                         volunteer_skill_ids: List[int]) -> Dict:
        """
        Get detailed skill match information for an emergency.
        
        Args:
            emergency: The emergency request
            volunteer_skill_ids: List of volunteer's verified skill IDs
            
        Returns:
            Dictionary with skill match details
        """
        mandatory_skill_ids = [rs.skill_id for rs in emergency.required_skills if rs.is_mandatory]
        optional_skill_ids = [rs.skill_id for rs in emergency.required_skills if not rs.is_mandatory]
        
        mandatory_matches = [skill_id for skill_id in mandatory_skill_ids 
                           if skill_id in volunteer_skill_ids]
        optional_matches = [skill_id for skill_id in optional_skill_ids 
                          if skill_id in volunteer_skill_ids]
        
        return {
            'mandatory_matches': len(mandatory_matches),
            'mandatory_total': len(mandatory_skill_ids),
            'optional_matches': len(optional_matches),
            'optional_total': len(optional_skill_ids),
            'has_all_mandatory': len(mandatory_matches) == len(mandatory_skill_ids)
        }
    
    @staticmethod
    def create_assignments(emergency: EmergencyRequest, 
                         volunteer_matches: List[Dict]) -> List[Assignment]:
        """
        Create assignments for the best matching volunteers.
        
        Args:
            emergency: The emergency request
            volunteer_matches: List of volunteer match dictionaries
            
        Returns:
            List of created assignments
        """
        assignments = []
        volunteers_needed = emergency.volunteers_needed
        
        # Sort by match score and take the best matches
        best_matches = sorted(volunteer_matches, 
                            key=lambda x: x['match_score'], reverse=True)
        
        for i, match in enumerate(best_matches[:volunteers_needed]):
            volunteer = match['volunteer']
            
            # Create assignment
            assignment = Assignment(
                emergency_id=emergency.id,
                volunteer_id=volunteer.id,
                status='requested'
            )
            
            db.session.add(assignment)
            assignments.append(assignment)
        
        return assignments
    
    @staticmethod
    def get_matching_statistics(emergency: EmergencyRequest) -> Dict:
        """
        Get statistics about volunteer matching for an emergency.
        
        Args:
            emergency: The emergency request
            
        Returns:
            Dictionary with matching statistics
        """
        # Find all potential matches (ignoring existing assignments)
        required_skill_ids = [rs.skill_id for rs in emergency.required_skills]
        
        volunteers_in_radius = LocationService.find_volunteers_in_radius(
            center_lat=float(emergency.latitude),
            center_lon=float(emergency.longitude),
            radius_km=emergency.search_radius_km,
            required_skill_ids=required_skill_ids if required_skill_ids else None,
            availability_filter=None  # Include all availability statuses
        )
        
        # Categorize volunteers
        available_volunteers = []
        busy_volunteers = []
        offline_volunteers = []
        
        for volunteer, distance in volunteers_in_radius:
            if volunteer.availability_status == 'available':
                available_volunteers.append((volunteer, distance))
            elif volunteer.availability_status == 'busy':
                busy_volunteers.append((volunteer, distance))
            else:
                offline_volunteers.append((volunteer, distance))
        
        # Get existing assignments
        existing_assignments = Assignment.query.filter_by(
            emergency_id=emergency.id
        ).count()
        
        return {
            'total_in_radius': len(volunteers_in_radius),
            'available_volunteers': len(available_volunteers),
            'busy_volunteers': len(busy_volunteers),
            'offline_volunteers': len(offline_volunteers),
            'existing_assignments': existing_assignments,
            'volunteers_needed': emergency.volunteers_needed,
            'volunteers_remaining': max(0, emergency.volunteers_needed - existing_assignments),
            'search_radius_km': emergency.search_radius_km,
            'required_skills_count': len(required_skill_ids)
        }
    
    @staticmethod
    def suggest_radius_expansion(emergency: EmergencyRequest) -> Dict:
        """
        Suggest radius expansion for emergencies with insufficient volunteers.
        
        Args:
            emergency: The emergency request
            
        Returns:
            Dictionary with expansion suggestions
        """
        current_stats = MatchingService.get_matching_statistics(emergency)
        
        if current_stats['available_volunteers'] >= emergency.volunteers_needed:
            return {
                'needs_expansion': False,
                'current_radius': emergency.search_radius_km,
                'suggested_radius': emergency.search_radius_km,
                'reason': 'Sufficient volunteers available'
            }
        
        # Try expanding radius
        max_radius = current_app.config.get('MAX_SEARCH_RADIUS_KM', 100)
        suggested_radius = LocationService.expand_search_radius(
            emergency.search_radius_km, max_radius
        )
        
        if suggested_radius <= emergency.search_radius_km:
            return {
                'needs_expansion': True,
                'current_radius': emergency.search_radius_km,
                'suggested_radius': suggested_radius,
                'reason': 'Already at maximum radius'
            }
        
        # Check how many volunteers would be available at expanded radius
        expanded_volunteers = LocationService.find_volunteers_in_radius(
            center_lat=float(emergency.latitude),
            center_lon=float(emergency.longitude),
            radius_km=suggested_radius,
            required_skill_ids=[rs.skill_id for rs in emergency.required_skills],
            availability_filter='available'
        )
        
        return {
            'needs_expansion': True,
            'current_radius': emergency.search_radius_km,
            'suggested_radius': suggested_radius,
            'current_available': current_stats['available_volunteers'],
            'expanded_available': len(expanded_volunteers),
            'additional_volunteers': len(expanded_volunteers) - current_stats['available_volunteers'],
            'reason': f'Would add {len(expanded_volunteers) - current_stats["available_volunteers"]} more volunteers'
        }