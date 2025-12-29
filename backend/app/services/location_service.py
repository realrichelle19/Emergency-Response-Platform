"""
Location-based services for the Emergency Response Platform.

This module provides geographic distance calculations and location-based
matching functionality using the Haversine formula for accurate distance
calculations on the Earth's surface.
"""

import math
from typing import List, Tuple, Optional
from flask import current_app
from app import db
from app.models import VolunteerProfile, EmergencyRequest
from sqlalchemy import and_, func

class LocationService:
    """Service class for location-based operations."""
    
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points on Earth using the Haversine formula.
        
        Args:
            lat1, lon1: Latitude and longitude of first point in decimal degrees
            lat2, lon2: Latitude and longitude of second point in decimal degrees
            
        Returns:
            Distance in kilometers
        """
        # Convert decimal degrees to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(dlon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        # Earth's radius in kilometers
        R = 6371.0
        distance = R * c
        
        return round(distance, 2)
    
    @staticmethod
    def get_bounding_box(lat: float, lon: float, radius_km: float) -> Tuple[float, float, float, float]:
        """
        Calculate bounding box coordinates for a given center point and radius.
        
        This is used for efficient database queries by filtering to a rectangular
        area before applying the more expensive distance calculation.
        
        Args:
            lat, lon: Center point coordinates
            radius_km: Radius in kilometers
            
        Returns:
            Tuple of (min_lat, max_lat, min_lon, max_lon)
        """
        # Approximate degrees per kilometer
        # 1 degree of latitude ≈ 111 km
        lat_delta = radius_km / 111.0
        
        # 1 degree of longitude varies by latitude
        # At the equator: 1 degree ≈ 111 km
        # At latitude φ: 1 degree ≈ 111 * cos(φ) km
        lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))
        
        min_lat = lat - lat_delta
        max_lat = lat + lat_delta
        min_lon = lon - lon_delta
        max_lon = lon + lon_delta
        
        # Ensure longitude stays within valid range
        min_lon = max(min_lon, -180.0)
        max_lon = min(max_lon, 180.0)
        
        # Ensure latitude stays within valid range
        min_lat = max(min_lat, -90.0)
        max_lat = min(max_lat, 90.0)
        
        return min_lat, max_lat, min_lon, max_lon
    
    @staticmethod
    def find_volunteers_in_radius(center_lat: float, center_lon: float, 
                                radius_km: float, required_skill_ids: List[int] = None,
                                availability_filter: str = 'available') -> List[Tuple[VolunteerProfile, float]]:
        """
        Find volunteers within a specified radius of a location.
        
        Args:
            center_lat, center_lon: Center point coordinates
            radius_km: Search radius in kilometers
            required_skill_ids: List of skill IDs that volunteers must have (verified)
            availability_filter: Filter by availability status ('available', 'busy', 'offline', or None for all)
            
        Returns:
            List of tuples (VolunteerProfile, distance_km) sorted by distance
        """
        from app.models.volunteer import VolunteerSkill
        
        # Get bounding box for efficient initial filtering
        min_lat, max_lat, min_lon, max_lon = LocationService.get_bounding_box(
            center_lat, center_lon, radius_km
        )
        
        # Build base query
        query = db.session.query(VolunteerProfile).filter(
            and_(
                VolunteerProfile.latitude.isnot(None),
                VolunteerProfile.longitude.isnot(None),
                VolunteerProfile.latitude.between(min_lat, max_lat),
                VolunteerProfile.longitude.between(min_lon, max_lon)
            )
        )
        
        # Filter by availability if specified
        if availability_filter:
            query = query.filter(VolunteerProfile.availability_status == availability_filter)
        
        # Filter by required skills if specified
        if required_skill_ids:
            # Volunteers must have at least one of the required skills (verified)
            query = query.join(VolunteerSkill).filter(
                and_(
                    VolunteerSkill.skill_id.in_(required_skill_ids),
                    VolunteerSkill.verification_status == 'verified'
                )
            ).distinct()
        
        # Get volunteers in bounding box
        volunteers = query.all()
        
        # Calculate exact distances and filter by radius
        volunteers_with_distance = []
        for volunteer in volunteers:
            distance = LocationService.calculate_distance(
                center_lat, center_lon,
                float(volunteer.latitude), float(volunteer.longitude)
            )
            
            if distance <= radius_km:
                volunteers_with_distance.append((volunteer, distance))
        
        # Sort by distance
        volunteers_with_distance.sort(key=lambda x: x[1])
        
        return volunteers_with_distance
    
    @staticmethod
    def find_emergencies_near_volunteer(volunteer_profile: VolunteerProfile,
                                      radius_km: float = None) -> List[Tuple[EmergencyRequest, float]]:
        """
        Find emergency requests near a volunteer's location.
        
        Args:
            volunteer_profile: The volunteer's profile
            radius_km: Search radius in kilometers (uses default if None)
            
        Returns:
            List of tuples (EmergencyRequest, distance_km) sorted by priority and distance
        """
        if not volunteer_profile.latitude or not volunteer_profile.longitude:
            return []
        
        if radius_km is None:
            radius_km = current_app.config.get('DEFAULT_SEARCH_RADIUS_KM', 25)
        
        # Get bounding box for efficient initial filtering
        min_lat, max_lat, min_lon, max_lon = LocationService.get_bounding_box(
            float(volunteer_profile.latitude), float(volunteer_profile.longitude), radius_km
        )
        
        # Find open emergencies in bounding box
        emergencies = db.session.query(EmergencyRequest).filter(
            and_(
                EmergencyRequest.status == 'open',
                EmergencyRequest.latitude.between(min_lat, max_lat),
                EmergencyRequest.longitude.between(min_lon, max_lon)
            )
        ).all()
        
        # Calculate exact distances and filter by radius
        emergencies_with_distance = []
        for emergency in emergencies:
            distance = LocationService.calculate_distance(
                float(volunteer_profile.latitude), float(volunteer_profile.longitude),
                float(emergency.latitude), float(emergency.longitude)
            )
            
            if distance <= radius_km:
                emergencies_with_distance.append((emergency, distance))
        
        # Sort by priority (higher priority first) then by distance
        priority_scores = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        emergencies_with_distance.sort(
            key=lambda x: (-priority_scores.get(x[0].priority_level, 0), x[1])
        )
        
        return emergencies_with_distance
    
    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> bool:
        """
        Validate that coordinates are within valid ranges.
        
        Args:
            lat: Latitude in decimal degrees
            lon: Longitude in decimal degrees
            
        Returns:
            True if coordinates are valid, False otherwise
        """
        return (-90.0 <= lat <= 90.0) and (-180.0 <= lon <= 180.0)
    
    @staticmethod
    def get_distance_between_profiles(profile1: VolunteerProfile, 
                                    profile2: VolunteerProfile) -> Optional[float]:
        """
        Calculate distance between two volunteer profiles.
        
        Args:
            profile1, profile2: Volunteer profiles
            
        Returns:
            Distance in kilometers, or None if either profile lacks coordinates
        """
        if (not profile1.latitude or not profile1.longitude or
            not profile2.latitude or not profile2.longitude):
            return None
        
        return LocationService.calculate_distance(
            float(profile1.latitude), float(profile1.longitude),
            float(profile2.latitude), float(profile2.longitude)
        )
    
    @staticmethod
    def get_distance_to_emergency(volunteer_profile: VolunteerProfile,
                                emergency: EmergencyRequest) -> Optional[float]:
        """
        Calculate distance from volunteer to emergency.
        
        Args:
            volunteer_profile: The volunteer's profile
            emergency: The emergency request
            
        Returns:
            Distance in kilometers, or None if volunteer lacks coordinates
        """
        if not volunteer_profile.latitude or not volunteer_profile.longitude:
            return None
        
        return LocationService.calculate_distance(
            float(volunteer_profile.latitude), float(volunteer_profile.longitude),
            float(emergency.latitude), float(emergency.longitude)
        )
    
    @staticmethod
    def expand_search_radius(current_radius: float, max_radius: float = None) -> float:
        """
        Expand search radius for emergency escalation.
        
        Args:
            current_radius: Current search radius in kilometers
            max_radius: Maximum allowed radius (uses config default if None)
            
        Returns:
            New expanded radius in kilometers
        """
        if max_radius is None:
            max_radius = current_app.config.get('MAX_SEARCH_RADIUS_KM', 100)
        
        # Double the radius, but don't exceed maximum
        new_radius = min(current_radius * 2, max_radius)
        
        return new_radius
    
    @staticmethod
    def get_coverage_area(volunteers: List[VolunteerProfile], 
                         radius_km: float = 10) -> Tuple[float, float, float, float]:
        """
        Calculate the bounding box that covers all volunteers with their service radius.
        
        Args:
            volunteers: List of volunteer profiles
            radius_km: Service radius for each volunteer
            
        Returns:
            Tuple of (min_lat, max_lat, min_lon, max_lon) covering all volunteers
        """
        if not volunteers:
            return 0.0, 0.0, 0.0, 0.0
        
        # Filter volunteers with valid coordinates
        valid_volunteers = [v for v in volunteers 
                          if v.latitude is not None and v.longitude is not None]
        
        if not valid_volunteers:
            return 0.0, 0.0, 0.0, 0.0
        
        # Find overall bounding box
        min_lat = min(float(v.latitude) for v in valid_volunteers)
        max_lat = max(float(v.latitude) for v in valid_volunteers)
        min_lon = min(float(v.longitude) for v in valid_volunteers)
        max_lon = max(float(v.longitude) for v in valid_volunteers)
        
        # Expand by service radius
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * math.cos(math.radians((min_lat + max_lat) / 2)))
        
        min_lat -= lat_delta
        max_lat += lat_delta
        min_lon -= lon_delta
        max_lon += lon_delta
        
        # Ensure coordinates stay within valid ranges
        min_lat = max(min_lat, -90.0)
        max_lat = min(max_lat, 90.0)
        min_lon = max(min_lon, -180.0)
        max_lon = min(max_lon, 180.0)
        
        return min_lat, max_lat, min_lon, max_lon