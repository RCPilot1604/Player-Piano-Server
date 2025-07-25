from flask import Blueprint

bp = Blueprint('categories', __name__)

from app.api.category import routes
