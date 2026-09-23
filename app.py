import os
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, send_from_directory, abort
)
from werkzeug.exceptions import RequestEntityTooLarge
from config import Config
from database import query_db, execute_db
from storage import save_resume, delete_resume, get_file_path
from auth import (
    hash_password, verify_password, get_current_user,
    calculate_profile_completion, login_required, admin_required, student_required
)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_CONTENT_LENGTH

VALID_STATUSES = ['Applied', 'Under Review', 'Shortlisted', 'Selected', 'Rejected']
VALID_TYPES = ['Remote', 'Hybrid', 'On-site']

# ---------------------------------------------------------------------------
# Public SaaS Routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    """Public SaaS marketing homepage."""
    total_internships = query_db("SELECT COUNT(*) as count FROM internships WHERE is_active = 1", one=True)['count']
    total_applications = query_db("SELECT COUNT(*) as count FROM applications", one=True)['count']
    total_students = query_db("SELECT COUNT(*) as count FROM users WHERE role = 'student'", one=True)['count']

    featured_internships = query_db(
        "SELECT * FROM internships WHERE is_active = 1 ORDER BY created_at DESC LIMIT 6"
    )

    return render_template(
        'index.html',
        total_internships=total_internships,
        total_applications=total_applications,
        total_students=total_students,
        featured_internships=featured_internships
    )

@app.route('/about')
def about():
    """Professional About Us & Platform Overview page."""
    return render_template('about.html')

# ---------------------------------------------------------------------------
# Authentication Routes (Registration, Login, Logout)
# ---------------------------------------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Student registration endpoint."""
    if 'user_id' in session:
        return redirect(url_for('student_dashboard' if session.get('user_role') == 'student' else 'admin_dashboard'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Optional profile fields during registration
        phone = request.form.get('phone', '').strip()
        college = request.form.get('college', '').strip()
        degree = request.form.get('degree', '').strip()
        graduation_year = request.form.get('graduation_year', '').strip()

        if not name or not email or not password:
            flash("Full name, email, and password are required.", "danger")
            return render_template('auth/register.html')

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('auth/register.html')

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth/register.html')

        # Check existing user
        existing_user = query_db("SELECT id FROM users WHERE email = ?", (email,), one=True)
        if existing_user:
            flash("An account with this email address already exists. Please sign in.", "warning")
            return redirect(url_for('login'))

        # Create student account
        pwd_hash = hash_password(password)
        execute_db(
            """INSERT INTO users 
               (name, email, password, role, phone, college, degree, graduation_year, is_active) 
               VALUES (?, ?, ?, 'student', ?, ?, ?, ?, 1)""",
            (name, email, pwd_hash, phone, college, degree, graduation_year)
        )

        flash("Account created successfully. Please sign in to continue.", "success")
        return redirect(url_for('login'))

    return render_template('auth/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Universal user login for Students and Administrators."""
    if 'user_id' in session:
        if session.get('user_role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template('auth/login.html')

        user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if not user or not verify_password(password, user['password']):
            flash("Invalid email or password. Please try again.", "danger")
            return render_template('auth/login.html')

        if not user.get('is_active', 1):
            flash("Your account has been deactivated. Please contact support.", "danger")
            return render_template('auth/login.html')

        # Set session
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['user_role'] = user['role']

        flash(f"Welcome back, {user['name']}.", "success")
        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))

    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    """Sign out active user and invalidate session."""
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for('login'))

# ---------------------------------------------------------------------------
# Internship Discovery Marketplace
# ---------------------------------------------------------------------------
@app.route('/internships')
def internships_list():
    """Search and filter available internship positions."""
    search_query = request.args.get('q', '').strip()
    location_filter = request.args.get('location', '').strip()
    type_filter = request.args.get('type', '').strip()
    duration_filter = request.args.get('duration', '').strip()
    skills_filter = request.args.get('skills', '').strip()

    sql = "SELECT * FROM internships WHERE is_active = 1"
    params = []

    if search_query:
        sql += " AND (title LIKE ? OR company LIKE ? OR skills LIKE ? OR description LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    if location_filter:
        sql += " AND location LIKE ?"
        params.append(f"%{location_filter}%")

    if type_filter:
        sql += " AND internship_type = ?"
        params.append(type_filter)

    if duration_filter:
        sql += " AND duration LIKE ?"
        params.append(f"%{duration_filter}%")

    if skills_filter:
        sql += " AND skills LIKE ?"
        params.append(f"%{skills_filter}%")

    sql += " ORDER BY created_at DESC"
    internships = query_db(sql, tuple(params))

    return render_template(
        'internships/list.html',
        internships=internships,
        query=search_query,
        location_filter=location_filter,
        type_filter=type_filter,
        duration_filter=duration_filter,
        skills_filter=skills_filter
    )

@app.route('/internships/<int:internship_id>')
def internship_detail(internship_id):
    """Detailed view for an internship listing."""
    internship = query_db("SELECT * FROM internships WHERE id = ?", (internship_id,), one=True)
    if not internship:
        abort(404)

    existing_application = None
    student_profile = None

    if 'user_id' in session:
        if session.get('user_role') == 'student':
            existing_application = query_db(
                "SELECT * FROM applications WHERE student_id = ? AND internship_id = ?",
                (session['user_id'], internship_id),
                one=True
            )
            student_profile = query_db(
                "SELECT resume_filename FROM users WHERE id = ?",
                (session['user_id'],),
                one=True
            )

    return render_template(
        'internships/detail.html',
        internship=internship,
        existing_application=existing_application,
        student_profile=student_profile
    )

@app.route('/internships/<int:internship_id>/apply', methods=['POST'])
@student_required
def apply_internship(internship_id):
    """Submits a student application with resume."""
    internship = query_db("SELECT id, title, is_active FROM internships WHERE id = ?", (internship_id,), one=True)
    if not internship or not internship['is_active']:
        flash("This internship listing is currently unavailable.", "warning")
        return redirect(url_for('internships_list'))

    student_id = session['user_id']

    # Duplicate check
    existing_app = query_db(
        "SELECT id FROM applications WHERE student_id = ? AND internship_id = ?",
        (student_id, internship_id),
        one=True
    )
    if existing_app:
        flash("You have already submitted an application for this position.", "warning")
        return redirect(url_for('internship_detail', internship_id=internship_id))

    resume_source = request.form.get('resume_source', 'upload')
    saved_filename = None

    if resume_source == 'profile':
        # Use existing profile resume
        user = query_db("SELECT resume_filename FROM users WHERE id = ?", (student_id,), one=True)
        if user and user.get('resume_filename'):
            saved_filename = user['resume_filename']
        else:
            flash("No resume found on your profile. Please upload a resume document.", "danger")
            return redirect(url_for('internship_detail', internship_id=internship_id))
    else:
        # Direct file upload
        if 'resume' not in request.files or request.files['resume'].filename == '':
            flash("Please upload your resume document.", "danger")
            return redirect(url_for('internship_detail', internship_id=internship_id))

        file = request.files['resume']
        try:
            saved_filename = save_resume(file)
            # Update user profile with latest resume if not already set
            execute_db("UPDATE users SET resume_filename = ? WHERE id = ? AND (resume_filename IS NULL OR resume_filename = '')",
                       (saved_filename, student_id))
        except ValueError as e:
            flash(str(e), "danger")
            return redirect(url_for('internship_detail', internship_id=internship_id))
        except Exception as e:
            flash(f"Error processing document: {str(e)}", "danger")
            return redirect(url_for('internship_detail', internship_id=internship_id))

    execute_db(
        """INSERT INTO applications 
           (student_id, internship_id, resume_filename, status) 
           VALUES (?, ?, ?, 'Applied')""",
        (student_id, internship_id, saved_filename)
    )

    flash("Your application was submitted successfully.", "success")
    return redirect(url_for('student_applications'))

# ---------------------------------------------------------------------------
# Student Portal (Dashboard, Applications Tracker, Profile)
# ---------------------------------------------------------------------------
@app.route('/student/dashboard')
@student_required
def student_dashboard():
    """Student career portal dashboard."""
    student_id = session['user_id']
    user = query_db("SELECT * FROM users WHERE id = ?", (student_id,), one=True)
    profile_completion = calculate_profile_completion(user)

    apps = query_db(
        """SELECT a.id, a.status, a.applied_at, a.resume_filename, a.internship_id,
                  i.title, i.company, i.location, i.internship_type
           FROM applications a
           JOIN internships i ON a.internship_id = i.id
           WHERE a.student_id = ?
           ORDER BY a.applied_at DESC""",
        (student_id,)
    )

    stats = {
        'total': len(apps),
        'under_review': sum(1 for a in apps if a['status'] == 'Under Review'),
        'shortlisted': sum(1 for a in apps if a['status'] == 'Shortlisted'),
        'selected': sum(1 for a in apps if a['status'] == 'Selected'),
        'rejected': sum(1 for a in apps if a['status'] == 'Rejected')
    }

    # Recommended internships (active postings not yet applied to)
    applied_ids = [a['internship_id'] for a in apps]
    if applied_ids:
        placeholders = ','.join(['?'] * len(applied_ids))
        recommended = query_db(
            f"SELECT * FROM internships WHERE is_active = 1 AND id NOT IN ({placeholders}) ORDER BY created_at DESC LIMIT 3",
            tuple(applied_ids)
        )
    else:
        recommended = query_db(
            "SELECT * FROM internships WHERE is_active = 1 ORDER BY created_at DESC LIMIT 3"
        )

    return render_template(
        'student/dashboard.html',
        user=user,
        stats=stats,
        profile_completion=profile_completion,
        recent_applications=apps[:5],
        recommended_internships=recommended
    )

@app.route('/student/applications')
@student_required
def student_applications():
    """Application tracking with visual pipeline progress."""
    student_id = session['user_id']
    applications = query_db(
        """SELECT a.id, a.status, a.applied_at, a.resume_filename, a.internship_id,
                  i.title, i.company, i.location, i.internship_type, i.deadline
           FROM applications a
           JOIN internships i ON a.internship_id = i.id
           WHERE a.student_id = ?
           ORDER BY a.applied_at DESC""",
        (student_id,)
    )
    return render_template('student/my_applications.html', applications=applications)

@app.route('/student/profile', methods=['GET', 'POST'])
@student_required
def student_profile():
    """Candidate career profile view and update."""
    student_id = session['user_id']
    user = query_db("SELECT * FROM users WHERE id = ?", (student_id,), one=True)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        college = request.form.get('college', '').strip()
        degree = request.form.get('degree', '').strip()
        graduation_year = request.form.get('graduation_year', '').strip()
        skills = request.form.get('skills', '').strip()
        linkedin_url = request.form.get('linkedin_url', '').strip()
        github_url = request.form.get('github_url', '').strip()

        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')

        if not name:
            flash("Full name cannot be empty.", "danger")
            return render_template('student/profile.html', user=user, profile_completion=calculate_profile_completion(user))

        execute_db(
            """UPDATE users 
               SET name = ?, phone = ?, college = ?, degree = ?, 
                   graduation_year = ?, skills = ?, linkedin_url = ?, github_url = ? 
               WHERE id = ?""",
            (name, phone, college, degree, graduation_year, skills, linkedin_url, github_url, student_id)
        )
        session['user_name'] = name

        # Password update
        if new_password:
            if not current_password:
                flash("Current password is required to set a new password.", "danger")
                user = query_db("SELECT * FROM users WHERE id = ?", (student_id,), one=True)
                return render_template('student/profile.html', user=user, profile_completion=calculate_profile_completion(user))

            if not verify_password(current_password, user['password']):
                flash("Current password is incorrect.", "danger")
                user = query_db("SELECT * FROM users WHERE id = ?", (student_id,), one=True)
                return render_template('student/profile.html', user=user, profile_completion=calculate_profile_completion(user))

            if len(new_password) < 6:
                flash("New password must be at least 6 characters long.", "danger")
                user = query_db("SELECT * FROM users WHERE id = ?", (student_id,), one=True)
                return render_template('student/profile.html', user=user, profile_completion=calculate_profile_completion(user))

            execute_db("UPDATE users SET password = ? WHERE id = ?", (hash_password(new_password), student_id))
            flash("Profile and password updated successfully.", "success")
        else:
            flash("Profile updated successfully.", "success")

        return redirect(url_for('student_profile'))

    profile_completion = calculate_profile_completion(user)
    return render_template('student/profile.html', user=user, profile_completion=profile_completion)

@app.route('/student/resume/upload', methods=['POST'])
@student_required
def student_resume_upload():
    """Upload or replace candidate's primary profile resume."""
    student_id = session['user_id']
    if 'resume' not in request.files or request.files['resume'].filename == '':
        flash("Please choose a file to upload.", "danger")
        return redirect(url_for('student_profile'))

    file = request.files['resume']
    try:
        user = query_db("SELECT resume_filename FROM users WHERE id = ?", (student_id,), one=True)
        old_filename = user.get('resume_filename') if user else None

        saved_filename = save_resume(file)
        execute_db("UPDATE users SET resume_filename = ? WHERE id = ?", (saved_filename, student_id))

        if old_filename and old_filename != saved_filename:
            delete_resume(old_filename)

        flash("Resume updated successfully.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Error saving resume: {str(e)}", "danger")

    return redirect(url_for('student_profile'))

@app.route('/student/resume/delete', methods=['POST'])
@student_required
def student_resume_delete():
    """Remove candidate's primary profile resume."""
    student_id = session['user_id']
    user = query_db("SELECT resume_filename FROM users WHERE id = ?", (student_id,), one=True)
    if user and user.get('resume_filename'):
        delete_resume(user['resume_filename'])
        execute_db("UPDATE users SET resume_filename = NULL WHERE id = ?", (student_id,))
        flash("Resume removed from your profile.", "info")
    return redirect(url_for('student_profile'))

# ---------------------------------------------------------------------------
# Administrator Console
# ---------------------------------------------------------------------------
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Administrative management dashboard."""
    total_internships = query_db("SELECT COUNT(*) as count FROM internships", one=True)['count']
    active_internships = query_db("SELECT COUNT(*) as count FROM internships WHERE is_active = 1", one=True)['count']
    total_students = query_db("SELECT COUNT(*) as count FROM users WHERE role = 'student'", one=True)['count']
    total_applications = query_db("SELECT COUNT(*) as count FROM applications", one=True)['count']

    status_rows = query_db("SELECT status, COUNT(*) as count FROM applications GROUP BY status")
    status_counts = {row['status']: row['count'] for row in status_rows}

    stats = {
        'total_internships': total_internships,
        'active_internships': active_internships,
        'total_students': total_students,
        'total_applications': total_applications,
        'status_counts': status_counts
    }

    recent_applications = query_db(
        """SELECT a.id, a.status, a.applied_at, a.resume_filename,
                  u.name as student_name, u.email as student_email,
                  i.title as internship_title
           FROM applications a
           JOIN users u ON a.student_id = u.id
           JOIN internships i ON a.internship_id = i.id
           ORDER BY a.applied_at DESC LIMIT 5"""
    )

    recent_postings = query_db(
        "SELECT * FROM internships ORDER BY created_at DESC LIMIT 4"
    )

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        recent_applications=recent_applications,
        recent_postings=recent_postings
    )

@app.route('/admin/internships')
@admin_required
def admin_internships():
    """Internship management table with search and status controls."""
    internships = query_db(
        """SELECT i.*, COUNT(a.id) as applicant_count
           FROM internships i
           LEFT JOIN applications a ON i.id = a.internship_id
           GROUP BY i.id
           ORDER BY i.created_at DESC"""
    )
    return render_template('admin/internships.html', internships=internships)

@app.route('/admin/internships/new', methods=['GET', 'POST'])
@admin_required
def admin_new_internship():
    """Create a new internship posting."""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        company = request.form.get('company', '').strip()
        description = request.form.get('description', '').strip()
        responsibilities = request.form.get('responsibilities', '').strip()
        required_skills = request.form.get('required_skills', '').strip()
        preferred_skills = request.form.get('preferred_skills', '').strip()
        location = request.form.get('location', '').strip()
        internship_type = request.form.get('internship_type', 'Remote').strip()
        skills = request.form.get('skills', '').strip()
        duration = request.form.get('duration', '').strip()
        deadline = request.form.get('deadline', '').strip()
        is_active = 1 if request.form.get('is_active') == '1' else 0

        if not all([title, company, description, location, skills, duration, deadline]):
            flash("Please complete all required fields.", "danger")
            return render_template('admin/internship_form.html', internship=None, valid_types=VALID_TYPES)

        execute_db(
            """INSERT INTO internships 
               (title, company, description, responsibilities, required_skills, preferred_skills,
                location, internship_type, skills, duration, deadline, is_active, is_sample) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (title, company, description, responsibilities, required_skills, preferred_skills,
             location, internship_type, skills, duration, deadline, is_active)
        )

        flash(f"Internship '{title}' has been published.", "success")
        return redirect(url_for('admin_internships'))

    return render_template('admin/internship_form.html', internship=None, valid_types=VALID_TYPES)

@app.route('/admin/internships/<int:internship_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_internship(internship_id):
    """Edit an existing internship posting."""
    internship = query_db("SELECT * FROM internships WHERE id = ?", (internship_id,), one=True)
    if not internship:
        abort(404)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        company = request.form.get('company', '').strip()
        description = request.form.get('description', '').strip()
        responsibilities = request.form.get('responsibilities', '').strip()
        required_skills = request.form.get('required_skills', '').strip()
        preferred_skills = request.form.get('preferred_skills', '').strip()
        location = request.form.get('location', '').strip()
        internship_type = request.form.get('internship_type', 'Remote').strip()
        skills = request.form.get('skills', '').strip()
        duration = request.form.get('duration', '').strip()
        deadline = request.form.get('deadline', '').strip()
        is_active = 1 if request.form.get('is_active') == '1' else 0

        if not all([title, company, description, location, skills, duration, deadline]):
            flash("Please complete all required fields.", "danger")
            return render_template('admin/internship_form.html', internship=internship, valid_types=VALID_TYPES)

        execute_db(
            """UPDATE internships 
               SET title = ?, company = ?, description = ?, responsibilities = ?, 
                   required_skills = ?, preferred_skills = ?, location = ?, 
                   internship_type = ?, skills = ?, duration = ?, deadline = ?, is_active = ? 
               WHERE id = ?""",
            (title, company, description, responsibilities, required_skills, preferred_skills,
             location, internship_type, skills, duration, deadline, is_active, internship_id)
        )

        flash("Internship details updated successfully.", "success")
        return redirect(url_for('admin_internships'))

    return render_template('admin/internship_form.html', internship=internship, valid_types=VALID_TYPES)

@app.route('/admin/internships/<int:internship_id>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_internship_status(internship_id):
    """Activate or deactivate an internship listing."""
    internship = query_db("SELECT id, title, is_active FROM internships WHERE id = ?", (internship_id,), one=True)
    if not internship:
        abort(404)

    new_status = 0 if internship['is_active'] else 1
    execute_db("UPDATE internships SET is_active = ? WHERE id = ?", (new_status, internship_id))

    status_str = "activated" if new_status else "deactivated"
    flash(f"Internship '{internship['title']}' has been {status_str}.", "info")
    return redirect(url_for('admin_internships'))

@app.route('/admin/internships/<int:internship_id>/delete', methods=['POST'])
@admin_required
def admin_delete_internship(internship_id):
    """Remove an internship listing and associated applications."""
    internship = query_db("SELECT id, title FROM internships WHERE id = ?", (internship_id,), one=True)
    if not internship:
        abort(404)

    execute_db("DELETE FROM internships WHERE id = ?", (internship_id,))
    flash(f"Internship '{internship['title']}' has been deleted.", "info")
    return redirect(url_for('admin_internships'))

@app.route('/admin/applications')
@admin_required
def admin_applications():
    """Candidate applications management with status and position filters."""
    internship_filter = request.args.get('internship_id', '').strip()
    status_filter = request.args.get('status', '').strip()

    sql = """SELECT a.id, a.status, a.applied_at, a.resume_filename,
                    u.id as student_id, u.name as student_name, u.email as student_email,
                    u.college as student_college,
                    i.id as internship_id, i.title as internship_title, i.company as internship_company
             FROM applications a
             JOIN users u ON a.student_id = u.id
             JOIN internships i ON a.internship_id = i.id
             WHERE 1=1"""
    params = []

    if internship_filter:
        sql += " AND a.internship_id = ?"
        params.append(internship_filter)

    if status_filter:
        sql += " AND a.status = ?"
        params.append(status_filter)

    sql += " ORDER BY a.applied_at DESC"
    applications = query_db(sql, tuple(params))

    all_internships = query_db("SELECT id, title, company FROM internships ORDER BY title ASC")

    return render_template(
        'admin/applications.html',
        applications=applications,
        internships=all_internships,
        selected_internship_id=internship_filter,
        selected_status=status_filter,
        valid_statuses=VALID_STATUSES
    )

@app.route('/admin/applications/<int:application_id>')
@admin_required
def admin_application_detail(application_id):
    """Candidate application review."""
    app_data = query_db(
        """SELECT a.id, a.status, a.applied_at, a.resume_filename, a.student_id, a.internship_id,
                  u.name as student_name, u.email as student_email, u.phone as student_phone,
                  u.college as student_college, u.degree as student_degree, u.skills as student_skills,
                  u.linkedin_url as student_linkedin, u.github_url as student_github,
                  i.title as internship_title, i.company as internship_company,
                  i.location as internship_location, i.duration as internship_duration
           FROM applications a
           JOIN users u ON a.student_id = u.id
           JOIN internships i ON a.internship_id = i.id
           WHERE a.id = ?""",
        (application_id,),
        one=True
    )
    if not app_data:
        abort(404)

    return render_template('admin/application_detail.html', application=app_data, valid_statuses=VALID_STATUSES)

@app.route('/admin/applications/<int:application_id>/status', methods=['POST'])
@admin_required
def admin_update_status(application_id):
    """Update candidate recruitment status."""
    new_status = request.form.get('status', '').strip()
    if new_status not in VALID_STATUSES:
        flash("Invalid status selection.", "danger")
        return redirect(url_for('admin_application_detail', application_id=application_id))

    execute_db("UPDATE applications SET status = ? WHERE id = ?", (new_status, application_id))
    flash(f"Application #{application_id} updated to '{new_status}'.", "success")
    return redirect(url_for('admin_application_detail', application_id=application_id))

@app.route('/admin/students')
@admin_required
def admin_students():
    """Directory of registered students."""
    students = query_db(
        """SELECT u.id, u.name, u.email, u.phone, u.college, u.degree, u.skills, u.is_active, u.created_at,
                  COUNT(a.id) as application_count
           FROM users u
           LEFT JOIN applications a ON u.id = a.student_id
           WHERE u.role = 'student'
           GROUP BY u.id
           ORDER BY u.created_at DESC"""
    )
    return render_template('admin/students.html', students=students)

@app.route('/admin/students/<int:student_id>')
@admin_required
def admin_student_detail(student_id):
    """Student profile inspection for recruiters/admins."""
    student = query_db(
        """SELECT id, name, email, phone, college, degree, graduation_year, 
                  skills, linkedin_url, github_url, resume_filename, is_active, created_at 
           FROM users WHERE id = ? AND role = 'student'""",
        (student_id,),
        one=True
    )
    if not student:
        abort(404)

    applications = query_db(
        """SELECT a.id, a.status, a.applied_at, a.resume_filename,
                  i.title as internship_title, i.company as internship_company
           FROM applications a
           JOIN internships i ON a.internship_id = i.id
           WHERE a.student_id = ?
           ORDER BY a.applied_at DESC""",
        (student_id,)
    )

    completion = calculate_profile_completion(student)
    return render_template('admin/student_detail.html', student=student, applications=applications, completion=completion)

@app.route('/admin/settings')
@admin_required
def admin_settings():
    """
    Administrative system diagnostics view.
    CRITICAL SECURITY RULE: Never display passwords, API keys, database credentials,
    AWS secrets, or .env secrets in this view!
    """
    system_info = {
        'app_name': 'InternTrack',
        'environment': 'Development' if Config.DEBUG else 'Production',
        'debug_mode': 'Enabled' if Config.DEBUG else 'Disabled',
        'database_driver': 'SQLite (Local Engine)' if Config.DB_TYPE == 'sqlite' else 'MySQL (RDS-Compatible Engine)',
        'storage_driver': 'Local Filesystem' if Config.STORAGE_TYPE == 'local' else 'Amazon S3 Document Store',
        'max_upload_size': f"{Config.MAX_CONTENT_LENGTH // (1024 * 1024)} MB",
        'allowed_file_types': ', '.join(sorted(Config.ALLOWED_EXTENSIONS)).upper(),
        'session_auth': 'Signed Client Session Cookies',
        'password_algorithm': 'PBKDF2:SHA256 (Werkzeug Security)'
    }
    return render_template('admin/settings.html', system_info=system_info)

# ---------------------------------------------------------------------------
# Secure File Serving Route
# ---------------------------------------------------------------------------
@app.route('/uploads/<path:filename>')
@login_required
def view_resume(filename):
    """
    Secure document viewer for resumes.
    Ensures students can view their own resume, and admins can view any candidate's resume.
    """
    if session.get('user_role') != 'admin':
        # Check if student owns the resume in applications or profile
        owned_in_app = query_db(
            "SELECT id FROM applications WHERE student_id = ? AND resume_filename = ?",
            (session['user_id'], filename),
            one=True
        )
        owned_in_profile = query_db(
            "SELECT id FROM users WHERE id = ? AND resume_filename = ?",
            (session['user_id'], filename),
            one=True
        )
        if not owned_in_app and not owned_in_profile:
            abort(403)

    return send_from_directory(Config.UPLOAD_FOLDER, filename)

# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(RequestEntityTooLarge)
def file_too_large_error(error):
    flash("The uploaded file exceeds the 5 MB maximum size limit.", "danger")
    return redirect(request.url)

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('errors/500.html'), 500

if __name__ == '__main__':
    port = Config.PORT
    debug_mode = Config.DEBUG
    print(f"[*] Starting InternTrack on http://127.0.0.1:{port} (Debug: {debug_mode})")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
