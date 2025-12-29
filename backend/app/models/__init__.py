# Import all models to ensure they are registered with SQLAlchemy
from app.models.user import User
from app.models.volunteer import VolunteerProfile, Skill, VolunteerSkill
from app.models.emergency import EmergencyRequest, EmergencyRequiredSkill
from app.models.assignment import Assignment
from app.models.activity_log import ActivityLog