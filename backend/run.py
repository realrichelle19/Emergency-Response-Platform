#!/usr/bin/env python3
"""
Emergency Response Platform - Application Entry Point

This script creates and runs the Flask application using the application factory pattern.
It handles environment configuration and provides CLI commands for database management.
"""

import os
from flask.cli import with_appcontext
import click
from app import create_app, db

# Create application instance
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

@app.cli.command()
@with_appcontext
def init_db():
    """Initialize the database with tables and sample data."""
    click.echo('Creating database tables...')
    db.create_all()
    
    # Import and run sample data creation
    from scripts.create_sample_data import create_sample_data
    create_sample_data()
    
    click.echo('Database initialized successfully!')

@app.cli.command()
@with_appcontext
def reset_db():
    """Reset the database (drop all tables and recreate)."""
    if click.confirm('This will delete all data. Are you sure?'):
        click.echo('Dropping all tables...')
        db.drop_all()
        click.echo('Creating database tables...')
        db.create_all()
        
        # Import and run sample data creation
        from scripts.create_sample_data import create_sample_data
        create_sample_data()
        
        click.echo('Database reset successfully!')

@app.shell_context_processor
def make_shell_context():
    """Make database and models available in Flask shell."""
    from app.models import User, VolunteerProfile, Skill, VolunteerSkill, EmergencyRequest, Assignment, ActivityLog
    return {
        'db': db,
        'User': User,
        'VolunteerProfile': VolunteerProfile,
        'Skill': Skill,
        'VolunteerSkill': VolunteerSkill,
        'EmergencyRequest': EmergencyRequest,
        'Assignment': Assignment,
        'ActivityLog': ActivityLog
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)