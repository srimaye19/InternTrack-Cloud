from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import query_db

def hash_password(password):
    """Hashes a plain text password using Werkzeug."""
    return generate_password_hash(password)

def verify_password(password, hashed_password):
    """Verifies a plain text password against the stored hash."""
    return check_password_hash(hashed_password, password)

def get_current_user():
    """Retrieves the currently logged-in user from the database based on session."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return query_db(
        """SELECT id, name, email, role, phone, college, degree, graduation_year, 
                  skills, linkedin_url, github_url, resume_filename, is_active, created_at 
           FROM users WHERE id = ?""",
        (user_id,),
        one=True
    )

def calculate_profile_completion(user):
    """
    Calculates candidate profile completion percentage (0 - 100%).
    Weights:
      Name: 10%
      Email: 10%
      Phone: 10%
      College: 15%
      Degree: 15%
      Graduation Year: 10%
      Skills: 15%
      Resume Uploaded: 15%
    """
    if not user:
        return 0

    score = 0
    if user.get('name'): score += 10
    if user.get('email'): score += 10
    if user.get('phone'): score += 10
    if user.get('college'): score += 15
    if user.get('degree'): score += 15
    if user.get('graduation_year'): score += 10
    if user.get('skills'): score += 15
    if user.get('resume_filename'): score += 15

    return min(score, 100)

def login_required(f):
    """Decorator to require user login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to restrict access strictly to administrators."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Administrator authentication required.", "warning")
            return redirect(url_for('login'))
        if session.get('user_role') != 'admin':
            flash("Access denied: Administrative privileges required.", "danger")
            return redirect(url_for('student_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    """Decorator to restrict access to students."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for('login'))
        if session.get('user_role') != 'student':
            flash("Redirected to administrative management console.", "info")
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function
