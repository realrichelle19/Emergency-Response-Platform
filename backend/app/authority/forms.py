"""
Authority forms for the Emergency Response Platform.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, FloatField, SubmitField, SelectMultipleField
from wtforms.validators import DataRequired, Length, NumberRange, Optional
from wtforms.widgets import CheckboxInput, ListWidget

class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()

class EmergencyRequestForm(FlaskForm):
    """Form for creating emergency requests."""
    title = StringField('Emergency Title', validators=[
        DataRequired(message='Title is required'),
        Length(min=5, max=200, message='Title must be between 5 and 200 characters')
    ])
    description = TextAreaField('Description', validators=[
        DataRequired(message='Description is required'),
        Length(min=10, max=1000, message='Description must be between 10 and 1000 characters')
    ])
    address = StringField('Address', validators=[
        Optional(),
        Length(max=300, message='Address must be less than 300 characters')
    ])
    latitude = FloatField('Latitude', validators=[
        Optional(),
        NumberRange(min=-90, max=90, message='Latitude must be between -90 and 90')
    ])
    longitude = FloatField('Longitude', validators=[
        Optional(),
        NumberRange(min=-180, max=180, message='Longitude must be between -180 and 180')
    ])
    priority_level = SelectField('Priority Level', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], validators=[
        DataRequired(message='Priority level is required')
    ])
    required_volunteers = IntegerField('Required Volunteers', validators=[
        DataRequired(message='Number of required volunteers is required'),
        NumberRange(min=1, max=50, message='Required volunteers must be between 1 and 50')
    ], default=1)
    search_radius_km = IntegerField('Search Radius (km)', validators=[
        DataRequired(message='Search radius is required'),
        NumberRange(min=1, max=100, message='Search radius must be between 1 and 100 km')
    ], default=10)
    required_skills = MultiCheckboxField('Required Skills', coerce=int)
    submit = SubmitField('Create Emergency Request')

class EditEmergencyForm(FlaskForm):
    """Form for editing emergency requests."""
    title = StringField('Emergency Title', validators=[
        DataRequired(message='Title is required'),
        Length(min=5, max=200, message='Title must be between 5 and 200 characters')
    ])
    description = TextAreaField('Description', validators=[
        DataRequired(message='Description is required'),
        Length(min=10, max=1000, message='Description must be between 10 and 1000 characters')
    ])
    address = StringField('Address', validators=[
        Optional(),
        Length(max=300, message='Address must be less than 300 characters')
    ])
    priority_level = SelectField('Priority Level', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], validators=[
        DataRequired(message='Priority level is required')
    ])
    required_volunteers = IntegerField('Required Volunteers', validators=[
        DataRequired(message='Number of required volunteers is required'),
        NumberRange(min=1, max=50, message='Required volunteers must be between 1 and 50')
    ])
    search_radius_km = IntegerField('Search Radius (km)', validators=[
        DataRequired(message='Search radius is required'),
        NumberRange(min=1, max=100, message='Search radius must be between 1 and 100 km')
    ])
    submit = SubmitField('Update Emergency Request')

class CompleteEmergencyForm(FlaskForm):
    """Form for completing emergency requests."""
    completion_notes = TextAreaField('Completion Notes', validators=[
        Optional(),
        Length(max=500, message='Notes must be less than 500 characters')
    ])
    submit = SubmitField('Mark as Completed')

class CancelEmergencyForm(FlaskForm):
    """Form for cancelling emergency requests."""
    reason = TextAreaField('Cancellation Reason', validators=[
        DataRequired(message='Cancellation reason is required'),
        Length(min=5, max=500, message='Reason must be between 5 and 500 characters')
    ])
    submit = SubmitField('Cancel Emergency')

class AssignVolunteerForm(FlaskForm):
    """Form for manually assigning volunteers."""
    volunteer_id = SelectField('Select Volunteer', coerce=int, validators=[
        DataRequired(message='Please select a volunteer')
    ])
    notes = TextAreaField('Assignment Notes', validators=[
        Optional(),
        Length(max=300, message='Notes must be less than 300 characters')
    ])
    submit = SubmitField('Assign Volunteer')