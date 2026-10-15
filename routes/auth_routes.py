import re
from functools import wraps
from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from routes import auth_bp
from database import query_db, execute_db

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Admin has super-permission over all student resources
        if session.get('admin_id'):
            return f(*args, **kwargs)
        if not session.get('student_id'):
            session['redirect_after_login'] = request.url
            flash("Please log in to continue.", "info")
            return redirect(url_for('auth.student_login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_id'):
            flash("Admin access required. Please log in.", "warning")
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ==================== STUDENT AUTH ====================

@auth_bp.route('/login', methods=['GET', 'POST'])
@auth_bp.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if session.get('student_id'):
        return redirect(url_for('student.index'))

    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            error = "Please fill in all fields."
        else:
            user = query_db(
                "SELECT * FROM users WHERE email = ? AND role = 'student'",
                (email,),
                one=True
            )
            if user and check_password_hash(user['password'], password):
                session['student_id'] = user['id']
                session['student_name'] = user['name']
                session['student_email'] = user['email']
                session['student_course_type'] = user.get('course_type', 'Degree')
                flash(f"Welcome back, {user['name']}! ({session['student_course_type']} Stream)", "success")

                redirect_url = session.pop('redirect_after_login', None)
                if redirect_url:
                    return redirect(redirect_url)
                return redirect(url_for('student.index'))
            else:
                error = "Invalid email or password."

    return render_template('auth/login.html', error=error)

@auth_bp.route('/register', methods=['GET', 'POST'])
@auth_bp.route('/student/register', methods=['GET', 'POST'])
def student_register():
    if session.get('student_id'):
        return redirect(url_for('student.index'))

    error = None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        mobile = request.form.get('mobile', '').strip()
        course_type = request.form.get('course_type', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not mobile or not password or not confirm_password or not course_type:
            error = "Please fill in all required fields including course stream (Diploma or Degree)."
        elif course_type not in ['Diploma', 'Degree']:
            error = "Please select a valid stream: Diploma or Degree."
        elif not re.match(r'^[0-9]{10}$', mobile):
            error = "Please enter a valid 10-digit mobile number."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters long."
        else:
            existing_email = query_db("SELECT id FROM users WHERE email = ?", (email,), one=True)
            if existing_email:
                error = "This email is already registered."
            else:
                existing_mobile = query_db("SELECT id FROM users WHERE mobile = ?", (mobile,), one=True)
                if existing_mobile:
                    error = "This mobile number is already registered."
                else:
                    hashed_pw = generate_password_hash(password)
                    user_id, _ = execute_db("""
                        INSERT INTO users (name, email, mobile, password, role, course_type)
                        VALUES (?, ?, ?, ?, 'student', ?)
                    """, (name, email, mobile, hashed_pw, course_type))
                    
                    session['student_id'] = user_id
                    session['student_name'] = name
                    session['student_email'] = email
                    session['student_course_type'] = course_type
                    flash(f"Registration successful! Welcome to TechEasy Tutorials ({course_type} Stream).", "success")
                    return redirect(url_for('student.index'))

    return render_template('auth/register.html', error=error)

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@auth_bp.route('/student/forgot-password', methods=['GET', 'POST'])
def student_forgot_password():
    error = None
    success = None
    verified = False
    reset_user_id = session.get('reset_student_id')

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'verify':
            email = request.form.get('email', '').strip()
            mobile = request.form.get('mobile', '').strip()

            if not email or not mobile:
                error = "Please enter your email and mobile number."
            elif not re.match(r'^[0-9]{10}$', mobile):
                error = "Please enter a valid 10-digit mobile number."
            else:
                user = query_db("""
                    SELECT id FROM users 
                    WHERE email = ? AND mobile = ? AND role = 'student'
                """, (email, mobile), one=True)
                if user:
                    session['reset_student_id'] = user['id']
                    verified = True
                    success = "Account verified! Please enter your new password below."
                else:
                    error = "Email and mobile number do not match our records."

        elif action == 'reset':
            if not reset_user_id:
                error = "Session expired. Please verify your account again."
            else:
                new_password = request.form.get('new_password', '')
                confirm_password = request.form.get('confirm_password', '')

                if not new_password or not confirm_password:
                    error = "Please enter both password fields."
                    verified = True
                elif new_password != confirm_password:
                    error = "Passwords do not match."
                    verified = True
                elif len(new_password) < 6:
                    error = "Password must be at least 6 characters long."
                    verified = True
                else:
                    hashed_pw = generate_password_hash(new_password)
                    execute_db("UPDATE users SET password = ? WHERE id = ?", (hashed_pw, reset_user_id))
                    session.pop('reset_student_id', None)
                    flash("Password has been successfully reset! You can now log in.", "success")
                    return redirect(url_for('auth.student_login'))

    if reset_user_id:
        verified = True

    return render_template('auth/forgot_password.html', error=error, success=success, verified=verified)

# ==================== ADMIN AUTH ====================

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_id'):
        return redirect(url_for('admin.dashboard'))

    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not email or not password:
            error = "Please fill in all fields."
        else:
            user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
            if not user:
                error = "Account not found."
            elif user['role'] != 'admin':
                error = "This account does not have administrator privileges."
            elif check_password_hash(user['password'], password):
                session['admin_id'] = user['id']
                session['admin_name'] = user['name']
                session['admin_email'] = user['email']
                flash(f"Welcome to Admin Panel, {user['name']}!", "success")
                return redirect(url_for('admin.dashboard'))
            else:
                error = "Incorrect password."

    return render_template('auth/admin_login.html', error=error)

# ==================== LOGOUT ====================

@auth_bp.route('/logout')
def student_logout():
    session.pop('student_id', None)
    session.pop('student_name', None)
    session.pop('student_email', None)
    session.pop('student_course_type', None)
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('student.index'))

@auth_bp.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    session.pop('admin_email', None)
    flash("Admin logged out.", "info")
    return redirect(url_for('auth.admin_login'))
