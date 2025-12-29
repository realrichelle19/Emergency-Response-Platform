from flask import Blueprint

bp = Blueprint('authority', __name__)

from app.authority import routes