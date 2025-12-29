from flask import Blueprint

bp = Blueprint('api', __name__)

# Import only the consolidated endpoints file to avoid duplicate routes
from app.api import all_endpoints