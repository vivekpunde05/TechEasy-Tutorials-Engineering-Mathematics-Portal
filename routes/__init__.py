from flask import Blueprint

auth_bp = Blueprint('auth', __name__)
student_bp = Blueprint('student', __name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
api_bp = Blueprint('api', __name__, url_prefix='/api')
