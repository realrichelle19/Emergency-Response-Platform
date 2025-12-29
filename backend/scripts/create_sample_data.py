#!/usr/bin/env python3
"""
Create sample data for the Emergency Response Platform.

This script creates sample users, skills, and emergency requests for development and testing.
"""

from app import db
from app.models import User, VolunteerProfile, Skill, VolunteerSkill, EmergencyRequest, EmergencyRequiredSkill
from datetime import datetime, timedelta, timezone
import random

def create_sample_data():
    """Create sample data for development and testing."""
    
    print("Creating sample skills...")
    create_skills()
    
    print("Creating sample users...")
    create_users()
    
    print("Creating sample volunteer profiles...")
    create_volunteer_profiles()
    
    print("Creating sample volunteer skills...")
    create_volunteer_skills()
    
    print("Creating sample emergency requests...")
    create_emergency_requests()
    
    db.session.commit()
    print("Sample data created successfully!")

def create_skills():
    """Create sample skills across different categories."""
    skills_data = [
        # Medical skills
        ('First Aid', 'medical', 'Basic first aid and CPR certification'),
        ('Emergency Medicine', 'medical', 'Advanced emergency medical treatment'),
        ('Nursing', 'medical', 'Professional nursing care'),
        ('Paramedic', 'medical', 'Advanced life support and emergency care'),
        ('Mental Health Support', 'medical', 'Crisis counseling and psychological first aid'),
        
        # Rescue skills
        ('Search and Rescue', 'rescue', 'Wilderness and urban search and rescue operations'),
        ('Water Rescue', 'rescue', 'Swift water and flood rescue operations'),
        ('Fire Fighting', 'rescue', 'Structural and wildland firefighting'),
        ('Technical Rescue', 'rescue', 'High angle, confined space, and technical rescue'),
        ('K9 Handler', 'rescue', 'Search and rescue dog handling'),
        
        # Logistics skills
        ('Supply Chain Management', 'logistics', 'Emergency supply distribution and management'),
        ('Transportation', 'logistics', 'Emergency transportation and evacuation'),
        ('Warehouse Operations', 'logistics', 'Emergency supply storage and distribution'),
        ('Food Service', 'logistics', 'Mass feeding and food preparation'),
        ('Shelter Management', 'logistics', 'Emergency shelter setup and management'),
        
        # Technical skills
        ('Communications', 'technical', 'Emergency communications and radio operations'),
        ('IT Support', 'technical', 'Emergency IT infrastructure and support'),
        ('Engineering', 'technical', 'Structural assessment and emergency repairs'),
        ('Heavy Equipment Operation', 'technical', 'Construction and earth-moving equipment'),
        ('Drone Operations', 'technical', 'Unmanned aerial vehicle operations for emergency response'),
        
        # Communication skills
        ('Translation', 'communication', 'Multi-language translation services'),
        ('Public Information', 'communication', 'Emergency public information and media relations'),
        ('Sign Language', 'communication', 'American Sign Language interpretation'),
        ('Community Outreach', 'communication', 'Community engagement and outreach'),
        
        # Other skills
        ('Administrative Support', 'other', 'Emergency operations administrative support'),
        ('Legal Aid', 'other', 'Emergency legal assistance and advocacy'),
        ('Childcare', 'other', 'Emergency childcare and family support'),
        ('Pet Care', 'other', 'Emergency animal care and sheltering'),
    ]
    
    for name, category, description in skills_data:
        if not Skill.query.filter_by(name=name).first():
            skill = Skill(name=name, category=category, description=description)
            db.session.add(skill)

def create_users():
    """Create sample users with different roles."""
    users_data = [
        # Admin users
        ('admin@emergency.local', 'admin', 'System', 'Administrator', '555-0001'),
        ('admin2@emergency.local', 'admin', 'Jane', 'Admin', '555-0002'),
        
        # Authority users
        ('fire.chief@emergency.local', 'authority', 'John', 'Smith', '555-1001'),
        ('police.captain@emergency.local', 'authority', 'Sarah', 'Johnson', '555-1002'),
        ('ems.director@emergency.local', 'authority', 'Michael', 'Brown', '555-1003'),
        ('emergency.manager@emergency.local', 'authority', 'Lisa', 'Davis', '555-1004'),
        ('red.cross@emergency.local', 'authority', 'David', 'Wilson', '555-1005'),
        
        # Volunteer users
        ('volunteer1@emergency.local', 'volunteer', 'Alice', 'Cooper', '555-2001'),
        ('volunteer2@emergency.local', 'volunteer', 'Bob', 'Miller', '555-2002'),
        ('volunteer3@emergency.local', 'volunteer', 'Carol', 'Garcia', '555-2003'),
        ('volunteer4@emergency.local', 'volunteer', 'Daniel', 'Martinez', '555-2004'),
        ('volunteer5@emergency.local', 'volunteer', 'Emma', 'Anderson', '555-2005'),
        ('volunteer6@emergency.local', 'volunteer', 'Frank', 'Taylor', '555-2006'),
        ('volunteer7@emergency.local', 'volunteer', 'Grace', 'Thomas', '555-2007'),
        ('volunteer8@emergency.local', 'volunteer', 'Henry', 'Jackson', '555-2008'),
        ('volunteer9@emergency.local', 'volunteer', 'Iris', 'White', '555-2009'),
        ('volunteer10@emergency.local', 'volunteer', 'Jack', 'Harris', '555-2010'),
    ]
    
    for email, role, first_name, last_name, phone in users_data:
        if not User.query.filter_by(email=email).first():
            user = User(
                email=email,
                role=role,
                first_name=first_name,
                last_name=last_name,
                phone=phone
            )
            user.set_password('password123')  # Default password for development
            db.session.add(user)

def create_volunteer_profiles():
    """Create volunteer profiles with locations around major cities."""
    # Sample locations around Seattle, WA area
    locations = [
        (47.6062, -122.3321, 'Seattle, WA'),      # Seattle downtown
        (47.6205, -122.3493, 'Seattle, WA'),      # Capitol Hill
        (47.5480, -122.3126, 'Seattle, WA'),      # Georgetown
        (47.6587, -122.3126, 'Seattle, WA'),      # Fremont
        (47.6740, -122.3861, 'Seattle, WA'),      # Ballard
        (47.7511, -122.3480, 'Seattle, WA'),      # Northgate
        (47.5014, -122.2370, 'Seattle, WA'),      # Beacon Hill
        (47.6815, -122.2065, 'Seattle, WA'),      # University District
        (47.5606, -122.2457, 'Seattle, WA'),      # Columbia City
        (47.6694, -122.3895, 'Seattle, WA'),      # Magnolia
    ]
    
    volunteer_users = User.query.filter_by(role='volunteer').all()
    availability_statuses = ['available', 'busy', 'offline']
    
    for i, user in enumerate(volunteer_users):
        if not user.volunteer_profile:
            location = locations[i % len(locations)]
            # Add some random variation to coordinates
            lat_variation = random.uniform(-0.01, 0.01)
            lon_variation = random.uniform(-0.01, 0.01)
            
            profile = VolunteerProfile(
                user_id=user.id,
                latitude=location[0] + lat_variation,
                longitude=location[1] + lon_variation,
                city=location[2],
                availability_status=random.choice(availability_statuses),
                bio=f"Experienced volunteer ready to help during emergencies. "
                    f"Available for {random.choice(['weekends', 'evenings', 'flexible hours'])}."
            )
            db.session.add(profile)

def create_volunteer_skills():
    """Create volunteer skills with various verification statuses."""
    volunteers = VolunteerProfile.query.all()
    skills = Skill.query.all()
    admin_users = User.query.filter_by(role='admin').all()
    
    verification_statuses = ['pending', 'verified', 'rejected']
    
    for volunteer in volunteers:
        # Each volunteer gets 2-5 random skills
        num_skills = random.randint(2, 5)
        volunteer_skills = random.sample(skills, num_skills)
        
        for skill in volunteer_skills:
            # Check if this volunteer-skill combination already exists
            existing = VolunteerSkill.query.filter_by(
                volunteer_id=volunteer.id,
                skill_id=skill.id
            ).first()
            
            if not existing:
                status = random.choice(verification_statuses)
                volunteer_skill = VolunteerSkill(
                    volunteer_id=volunteer.id,
                    skill_id=skill.id,
                    verification_status=status
                )
                
                # If verified or rejected, add verification details
                if status in ['verified', 'rejected']:
                    volunteer_skill.verified_by = random.choice(admin_users).id
                    volunteer_skill.verified_at = datetime.now(timezone.utc) - timedelta(
                        days=random.randint(1, 30)
                    )
                    if status == 'rejected':
                        volunteer_skill.verification_notes = "Insufficient documentation provided"
                    else:
                        volunteer_skill.verification_notes = "Documentation verified successfully"
                
                db.session.add(volunteer_skill)

def create_emergency_requests():
    """Create sample emergency requests."""
    authority_users = User.query.filter_by(role='authority').all()
    skills = Skill.query.all()
    
    # Sample emergency scenarios
    emergencies_data = [
        {
            'title': 'Apartment Fire - Medical Support Needed',
            'description': 'Multi-unit apartment fire with potential casualties. Need medical personnel for triage and treatment.',
            'priority_level': 'high',
            'required_volunteers': 3,
            'location': (47.6062, -122.3321, '123 Main St, Seattle, WA'),
            'required_skills': ['First Aid', 'Emergency Medicine', 'Nursing'],
            'status': 'open'
        },
        {
            'title': 'Flash Flood - Search and Rescue',
            'description': 'Flash flooding in residential area. Multiple people reported missing.',
            'priority_level': 'critical',
            'required_volunteers': 5,
            'location': (47.5480, -122.3126, '456 River Rd, Seattle, WA'),
            'required_skills': ['Search and Rescue', 'Water Rescue', 'First Aid'],
            'status': 'open'
        },
        {
            'title': 'Earthquake Response - Shelter Setup',
            'description': 'Major earthquake damage. Need volunteers to set up emergency shelters.',
            'priority_level': 'high',
            'required_volunteers': 8,
            'location': (47.6587, -122.3126, '789 Community Center Dr, Seattle, WA'),
            'required_skills': ['Shelter Management', 'Supply Chain Management', 'Food Service'],
            'status': 'assigned'
        },
        {
            'title': 'Wildfire Evacuation Support',
            'description': 'Wildfire approaching residential areas. Need transportation and logistics support.',
            'priority_level': 'critical',
            'required_volunteers': 6,
            'location': (47.7511, -122.3480, '321 Forest Ave, Seattle, WA'),
            'required_skills': ['Transportation', 'Communications', 'Administrative Support'],
            'status': 'open'
        },
        {
            'title': 'Chemical Spill - Technical Assessment',
            'description': 'Industrial chemical spill requiring technical assessment and cleanup coordination.',
            'priority_level': 'medium',
            'required_volunteers': 2,
            'location': (47.5014, -122.2370, '654 Industrial Blvd, Seattle, WA'),
            'required_skills': ['Engineering', 'IT Support', 'Communications'],
            'status': 'completed'
        }
    ]
    
    for emergency_data in emergencies_data:
        authority = random.choice(authority_users)
        location = emergency_data['location']
        
        emergency = EmergencyRequest(
            authority_id=authority.id,
            title=emergency_data['title'],
            description=emergency_data['description'],
            latitude=location[0],
            longitude=location[1],
            address=location[2],
            priority_level=emergency_data['priority_level'],
            status=emergency_data['status'],
            required_volunteers=emergency_data['required_volunteers'],
            search_radius_km=random.randint(10, 25),
            created_at=datetime.now(timezone.utc) - timedelta(
                hours=random.randint(1, 48)
            )
        )
        
        db.session.add(emergency)
        db.session.flush()  # Get the emergency ID
        
        # Add required skills
        for skill_name in emergency_data['required_skills']:
            skill = Skill.query.filter_by(name=skill_name).first()
            if skill:
                required_skill = EmergencyRequiredSkill(
                    emergency_id=emergency.id,
                    skill_id=skill.id,
                    is_mandatory=True
                )
                db.session.add(required_skill)

if __name__ == '__main__':
    from app import create_app
    app = create_app()
    
    with app.app_context():
        create_sample_data()