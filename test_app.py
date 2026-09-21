import os
import io
import unittest
import tempfile
from config import Config

# Point to temporary test directory
temp_dir = tempfile.TemporaryDirectory()
test_db_path = os.path.join(temp_dir.name, 'test_interntrack.db')
test_upload_folder = os.path.join(temp_dir.name, 'test_uploads')
os.makedirs(test_upload_folder, exist_ok=True)

Config.DB_TYPE = 'sqlite'
Config.SQLITE_DB_PATH = test_db_path
Config.UPLOAD_FOLDER = test_upload_folder
Config.STORAGE_TYPE = 'local'

from app import app
from database import init_db, query_db, execute_db
from auth import hash_password, calculate_profile_completion

class InternTrackComprehensiveTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()

        # Initialize test schema
        init_db()

        # Create demo admin
        self.admin_email = "admin@platform.com"
        self.admin_pass = "AdminSecurePass!123"
        self.admin_id, _ = execute_db(
            "INSERT INTO users (name, email, password, role, is_active) VALUES (?, ?, ?, 'admin', 1)",
            ("Platform Admin", self.admin_email, hash_password(self.admin_pass))
        )

        # Create demo student
        self.student_email = "alex@example.com"
        self.student_pass = "StudentPass!123"
        self.student_id, _ = execute_db(
            """INSERT INTO users 
               (name, email, password, role, phone, college, degree, graduation_year, skills, is_active) 
               VALUES (?, ?, ?, 'student', ?, ?, ?, ?, ?, 1)""",
            ("Alex Candidate", self.student_email, hash_password(self.student_pass),
             "+1555123456", "Tech University", "B.S. Computer Science", "2027", "Python, Docker, SQL")
        )

        # Create a sample active internship
        self.internship_id, _ = execute_db(
            """INSERT INTO internships 
               (title, company, description, responsibilities, required_skills, preferred_skills,
                location, internship_type, skills, duration, deadline, is_active, is_sample)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)""",
            (
                "Cloud Systems Intern",
                "CloudTech Labs",
                "Work on resilient cloud backend architecture.",
                "Build automated CI/CD pipelines.",
                "Python, Linux fundamentals.",
                "Docker, AWS knowledge.",
                "San Jose, CA",
                "Remote",
                "Python, Docker, Linux",
                "3 Months",
                "2026-12-31"
            )
        )

    def tearDown(self):
        execute_db("DELETE FROM applications")
        execute_db("DELETE FROM internships")
        execute_db("DELETE FROM users")

    def login(self, email, password):
        return self.client.post('/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    # -----------------------------------------------------------------------
    # Public & Landing Page Tests
    # -----------------------------------------------------------------------
    def test_01_public_pages(self):
        """Test home landing page and about page load properly with branding."""
        res_home = self.client.get('/')
        self.assertEqual(res_home.status_code, 200)
        self.assertIn(b"InternTrack", res_home.data)
        self.assertIn(b"Find the right internship", res_home.data)
        self.assertIn(b"Cloud Systems Intern", res_home.data)

        # Verify prohibited terms are NOT in the public page
        self.assertNotIn(b"college project", res_home.data.lower())
        self.assertNotIn(b"internship report", res_home.data.lower())

        res_about = self.client.get('/about')
        self.assertEqual(res_about.status_code, 200)
        self.assertIn(b"About InternTrack", res_about.data)

    # -----------------------------------------------------------------------
    # Authentication Tests
    # -----------------------------------------------------------------------
    def test_02_registration_and_validation(self):
        """Test student self-registration and duplicate prevention."""
        res = self.client.post('/register', data={
            'name': 'Taylor Swift',
            'email': 'taylor@example.com',
            'password': 'StrongPassword123',
            'confirm_password': 'StrongPassword123',
            'college': 'Music State',
            'degree': 'B.A. Audio'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Account created successfully", res.data)

        # Duplicate email
        res_dup = self.client.post('/register', data={
            'name': 'Duplicate Person',
            'email': 'taylor@example.com',
            'password': 'StrongPassword123',
            'confirm_password': 'StrongPassword123'
        }, follow_redirects=True)
        self.assertIn(b"already exists", res_dup.data)

    def test_03_login_and_logout(self):
        """Test user login and session clearance."""
        res = self.login(self.student_email, self.student_pass)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Alex Candidate", res.data)

        res_logout = self.logout()
        self.assertIn(b"signed out", res_logout.data)

        # Verify invalid password rejected
        res_bad = self.login(self.student_email, "WrongPass123")
        self.assertIn(b"Invalid email or password", res_bad.data)

    def test_04_role_authorization_boundaries(self):
        """Verify strict authorization preventing students/anonymous from accessing admin routes."""
        # Anonymous tries to access admin
        res_anon = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b"Administrator authentication required", res_anon.data)

        # Student tries to access admin
        self.login(self.student_email, self.student_pass)
        res_student_blocked = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertIn(b"Access denied", res_student_blocked.data)

    # -----------------------------------------------------------------------
    # Internship Marketplace & Filtering Tests
    # -----------------------------------------------------------------------
    def test_05_internship_filtering(self):
        """Test multi-parameter marketplace search and filtering."""
        res_search = self.client.get('/internships?q=Cloud')
        self.assertEqual(res_search.status_code, 200)
        self.assertIn(b"Cloud Systems Intern", res_search.data)

        res_type = self.client.get('/internships?type=Remote')
        self.assertEqual(res_type.status_code, 200)
        self.assertIn(b"Cloud Systems Intern", res_type.data)

        res_nomatch = self.client.get('/internships?q=NonExistentKeywordXYZ')
        self.assertEqual(res_nomatch.status_code, 200)
        self.assertIn(b"No internships match your search", res_nomatch.data)

    # -----------------------------------------------------------------------
    # Student Application & Resume Management Tests
    # -----------------------------------------------------------------------
    def test_06_application_submission_and_duplicate_prevention(self):
        """Test applying with a resume, duplicate prevention, and file validation."""
        self.login(self.student_email, self.student_pass)

        # Bad file extension
        bad_file = (io.BytesIO(b"binary payload"), "exploit.sh")
        res_bad = self.client.post(
            f'/internships/{self.internship_id}/apply',
            data={'resume': bad_file, 'resume_source': 'upload'},
            content_type='multipart/form-data',
            follow_redirects=True
        )
        self.assertIn(b"Unsupported file format", res_bad.data)

        # Valid PDF upload
        pdf_file = (io.BytesIO(b"%PDF-1.4 test document"), "alex_resume.pdf")
        res_good = self.client.post(
            f'/internships/{self.internship_id}/apply',
            data={'resume': pdf_file, 'resume_source': 'upload'},
            content_type='multipart/form-data',
            follow_redirects=True
        )
        self.assertEqual(res_good.status_code, 200)
        self.assertIn(b"Your application was submitted successfully", res_good.data)

        # Check database
        app_record = query_db(
            "SELECT * FROM applications WHERE student_id = ? AND internship_id = ?",
            (self.student_id, self.internship_id),
            one=True
        )
        self.assertIsNotNone(app_record)
        self.assertEqual(app_record['status'], 'Applied')

        # Duplicate submission check
        pdf_file2 = (io.BytesIO(b"%PDF-1.4 duplicate"), "alex_resume2.pdf")
        res_dup = self.client.post(
            f'/internships/{self.internship_id}/apply',
            data={'resume': pdf_file2, 'resume_source': 'upload'},
            content_type='multipart/form-data',
            follow_redirects=True
        )
        self.assertIn(b"already submitted an application", res_dup.data)

    def test_07_student_profile_and_resume_management(self):
        """Test candidate profile updates, completion scoring, and resume replacement."""
        self.login(self.student_email, self.student_pass)

        # Upload master resume to profile
        master_resume = (io.BytesIO(b"%PDF-1.4 master resume"), "master_alex.pdf")
        res_upload = self.client.post(
            '/student/resume/upload',
            data={'resume': master_resume},
            content_type='multipart/form-data',
            follow_redirects=True
        )
        self.assertEqual(res_upload.status_code, 200)
        self.assertIn(b"Resume updated successfully", res_upload.data)

        # Verify profile completion calculation
        user = query_db("SELECT * FROM users WHERE id = ?", (self.student_id,), one=True)
        completion = calculate_profile_completion(user)
        self.assertGreaterEqual(completion, 70)

        # Delete resume from profile
        res_del = self.client.post('/student/resume/delete', follow_redirects=True)
        self.assertIn(b"Resume removed from your profile", res_del.data)

    # -----------------------------------------------------------------------
    # Administrator Console Tests
    # -----------------------------------------------------------------------
    def test_08_admin_internship_management(self):
        """Test admin posting, editing, toggling status, and deleting positions."""
        self.login(self.admin_email, self.admin_pass)

        # Create new position
        res_new = self.client.post('/admin/internships/new', data={
            'title': 'AI Operations Intern',
            'company': 'NeuralTech Systems',
            'description': 'Help deploy machine learning pipelines.',
            'responsibilities': 'Deploy model serving endpoints.',
            'required_skills': 'Python, PyTorch.',
            'preferred_skills': 'Docker, AWS.',
            'location': 'Seattle, WA',
            'internship_type': 'Hybrid',
            'skills': 'Python, PyTorch, Docker',
            'duration': '6 Months',
            'deadline': '2026-11-30',
            'is_active': '1'
        }, follow_redirects=True)
        self.assertEqual(res_new.status_code, 200)
        self.assertIn(b"AI Operations Intern", res_new.data)

        created = query_db("SELECT id, is_active FROM internships WHERE title = 'AI Operations Intern'", one=True)
        self.assertIsNotNone(created)
        pos_id = created['id']
        self.assertEqual(created['is_active'], 1)

        # Toggle visibility to Inactive
        res_toggle = self.client.post(f'/admin/internships/{pos_id}/toggle-status', follow_redirects=True)
        self.assertEqual(res_toggle.status_code, 200)
        toggled = query_db("SELECT is_active FROM internships WHERE id = ?", (pos_id,), one=True)
        self.assertEqual(toggled['is_active'], 0)

        # Delete position
        res_del = self.client.post(f'/admin/internships/{pos_id}/delete', follow_redirects=True)
        self.assertIn(b"has been deleted", res_del.data)
        deleted = query_db("SELECT id FROM internships WHERE id = ?", (pos_id,), one=True)
        self.assertIsNone(deleted)

    def test_09_admin_pipeline_status_updates(self):
        """Test admin updating candidate status through all 5 recruitment stages."""
        # 1. Student applies
        self.login(self.student_email, self.student_pass)
        pdf = (io.BytesIO(b"%PDF-1.4 test application"), "candidate_cv.pdf")
        self.client.post(
            f'/internships/{self.internship_id}/apply',
            data={'resume': pdf, 'resume_source': 'upload'},
            content_type='multipart/form-data',
            follow_redirects=True
        )
        self.logout()

        # 2. Admin logs in and updates status
        self.login(self.admin_email, self.admin_pass)
        app_item = query_db("SELECT id FROM applications WHERE student_id = ?", (self.student_id,), one=True)
        self.assertIsNotNone(app_item)
        app_id = app_item['id']

        # Cycle through stages: Under Review -> Shortlisted -> Selected -> Rejected
        for stage in ['Under Review', 'Shortlisted', 'Selected', 'Rejected']:
            res = self.client.post(f'/admin/applications/{app_id}/status', data={
                'status': stage
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(stage.encode(), res.data)

            # Check database
            updated = query_db("SELECT status FROM applications WHERE id = ?", (app_id,), one=True)
            self.assertEqual(updated['status'], stage)

    def test_10_admin_student_directory_and_settings(self):
        """Test admin student directory inspection and settings diagnostics without credential leakage."""
        self.login(self.admin_email, self.admin_pass)

        # Students directory
        res_students = self.client.get('/admin/students')
        self.assertEqual(res_students.status_code, 200)
        self.assertIn(b"Alex Candidate", res_students.data)

        # Student detail inspection
        res_detail = self.client.get(f'/admin/students/{self.student_id}')
        self.assertEqual(res_detail.status_code, 200)
        self.assertIn(b"Tech University", res_detail.data)

        # Settings inspection - verify NO passwords, secrets, or keys exist in the output!
        res_settings = self.client.get('/admin/settings')
        self.assertEqual(res_settings.status_code, 200)
        self.assertIn(b"Runtime Environment", res_settings.data)
        self.assertIn(b"SQLite (Local Engine)", res_settings.data)
        self.assertNotIn(b"AdminSecurePass", res_settings.data)
        self.assertNotIn(b"SECRET_KEY", res_settings.data)
        self.assertNotIn(b"AWS_SECRET_ACCESS_KEY", res_settings.data)

if __name__ == '__main__':
    unittest.main()
