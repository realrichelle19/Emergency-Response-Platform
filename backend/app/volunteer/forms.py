"""
Volunteer forms for the Emergency Response Platform.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Optional, Email

class VolunteerProfileForm(FlaskForm):
    """Volunteer profile form."""
    first_name = StringField('First Name', validators=[
        DataRequired(message='First name is required'),
        Length(min=1, max=100, message='First name must be between 1 and 100 characters')
    ])
    last_name = StringField('Last Name', validators=[
        DataRequired(message='Last name is required'),
        Length(min=1, max=100, message='Last name must be between 1 and 100 characters')
    ])
    email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        Email(message='Please enter a valid email address')
    ])
    phone = StringField('Phone Number', validators=[
        Optional(),
        Length(max=20, message='Phone number must be less than 20 characters')
    ])
    city = StringField('City', validators=[
        Optional(),
        Length(max=100, message='City must be less than 100 characters')
    ])
    availability_status = SelectField('Availability Status', choices=[
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('offline', 'Offline')
    ], validators=[
        DataRequired(message='Please select availability status')
    ])
    bio = TextAreaField('Bio', validators=[
        Optional(),
        Length(max=500, message='Bio must be less than 500 characters')
    ])
    latitude = HiddenField('Latitude')
    longitude = HiddenField('Longitude')
    submit = SubmitField('Update Profile')

class AddSkillForm(FlaskForm):
    """Form to add a skill to volunteer profile."""
    skill_id = SelectField('Skill', coerce=int, validators=[
        DataRequired(message='Please select a skill')
    ])
    submit = SubmitField('Add Skill')

class AssignmentResponseForm(FlaskForm):
    """Form to respond to assignment requests."""
    response = SelectField('Response', choices=[
        ('accept', 'Accept'),
        ('decline', 'Decline')
    ], validators=[
        DataRequired(message='Please select a response')
    ])
    notes = TextAreaField('Notes', validators=[
        Optional(),
        Length(max=500, message='Notes must be less than 500 characters')
    ])
    submit = SubmitField('Submit Response')

class CompleteAssignmentForm(FlaskForm):
    """Form to complete an assignment."""
    notes = TextAreaField('Completion Notes', validators=[
        Optional(),
        Length(max=500, message='Notes must be less than 500 characters')
    ])
    submit = SubmitField('Mark as Completed')

class AvailabilityForm(FlaskForm):
    """Form to update availability status."""
    status = SelectField('Availability Status', choices=[
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('offline', 'Offline')
    ], validators=[
        DataRequired(message='Please select availability status')
    ])
    submit = SubmitField('Update Status')