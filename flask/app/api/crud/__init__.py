from flask import Blueprint

bp = Blueprint('crud', __name__)

from app.api.crud import routes