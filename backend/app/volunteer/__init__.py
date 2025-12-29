from flask import Blueprint

bp = Blueprint('volunteer', __name__)

from app.volunteer import routes