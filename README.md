# InternTrack – Modern Internship Management Platform

> **Discover opportunities. Build your future.**  
> A secure, role-based internship management web application engineered for scalable candidate recruitment and application tracking.

---

## 🌟 Overview

**InternTrack** is a modern, SaaS-style internship management platform that connects technical candidates with verified internship opportunities. Designed with clean engineering standards and cloud readiness, the platform provides candidates with a transparent application pipeline and gives recruiters an administrative management console to manage listings and progress applicants.

### Architectural Philosophy
- **Phase 1 (Current):** Standalone local foundation utilizing SQLite and a modular file storage abstraction.
- **Phase 2 (Cloud Deployment):** Cloud-first architecture ready for **Amazon EC2**, **Amazon RDS (MySQL)**, and **Amazon S3** by toggling environment variables without modifying application code.

---

## 🚀 Key Features

### For Candidates
- **Curated Internship Marketplace:** Search positions by keywords, location, workplace type (Remote, Hybrid, On-site), duration, and technical skills.
- **Role Specifications:** Detailed job listings with responsibilities, required qualifications, and preferred skills.
- **Master Resume & One-Click Apply:** Upload a master resume to your candidate profile for quick submissions or attach tailored documents per position.
- **Visual Application Tracker:** Real-time milestone tracker following applications through each stage: `Applied` &rarr; `Under Review` &rarr; `Shortlisted` &rarr; `Selected` (or `Rejected`).
- **Comprehensive Career Profile:** Track your education, technical competencies, social links (LinkedIn, GitHub), and profile completion strength.

### For Administrators
- **Executive Console:** High-level metrics on active positions, applicant volume, and recruitment stage distributions.
- **Position Lifecycle Management:** Full CRUD capabilities with instant visibility toggling (Active/Inactive) and cascade cleanup.
- **Candidate Pipeline Control:** Multi-criteria application filtering, resume inspection, and stage progression controls.
- **Student Directory:** Candidate roster with contact details, academic background, tagged competencies, and submission history.
- **Secure Diagnostics:** Non-sensitive operational inspection covering database drivers, storage engines, and environment modes without exposing credentials.

---

## 🛠️ Technology Stack

| Layer | Local Development | Cloud Target |
| :--- | :--- | :--- |
| **Runtime** | Python 3.12 | Python 3.12 (Amazon Linux / Ubuntu) |
| **Web Framework** | Flask 3.1.3 + Jinja2 + Werkzeug | Flask + Gunicorn WSGI Server |
| **Relational Database** | SQLite 3 (Foreign keys enabled) | Amazon RDS (MySQL 8.0) |
| **Document Storage** | Local Isolated Directory (`uploads/`) | Amazon Simple Storage Service (S3) |
| **Cloud SDK** | `boto3` (Prepared abstraction) | `boto3` (IAM Role integration) |
| **Security Standard** | Werkzeug PBKDF2:SHA256, Signed Sessions | AWS IAM, VPC, TLS/HTTPS |

---

## 📂 Project Structure

```
InternTrack-Cloud/
│
├── app.py                     # Main application entry point and route controllers
├── config.py                  # Environment-driven configuration loader
├── database.py                # Database connection & query abstraction (SQLite/MySQL)
├── storage.py                 # File storage handler (Local uploads / AWS S3 via boto3)
├── auth.py                    # Session auth, password hashing, and role decorators
├── create_admin.py            # Secure interactive CLI utility for administrator accounts
├── init_db.py                 # Database schema initialization and sample data seeder
├── test_app.py                # Automated test suite (10 comprehensive tests)
│
├── templates/                 # Responsive HTML5 Jinja2 templates
│   ├── base.html              # Core SaaS layout with responsive navigation
│   ├── index.html             # Public SaaS landing page
│   ├── about.html             # Platform mission and values overview
│   ├── auth/
│   │   ├── login.html         # Secure sign-in portal
│   │   └── register.html      # Candidate registration form
│   ├── student/
│   │   ├── dashboard.html     # Candidate portal with metrics & profile strength
│   │   ├── profile.html       # Candidate profile and master resume manager
│   │   └── my_applications.html # Visual stepper application tracker
│   ├── internships/
│   │   ├── list.html          # Marketplace catalog with multi-field search
│   │   └── detail.html        # Detailed role view and application form
│   ├── admin/
│   │   ├── layout.html        # Admin console layout with persistent sidebar
│   │   ├── dashboard.html     # Administrative metrics and pipeline breakdown
│   │   ├── internships.html   # Position management and visibility toggles
│   │   ├── internship_form.html # Create / Edit position specifications
│   │   ├── applications.html  # Submissions review and status filters
│   │   ├── application_detail.html # Application review and pipeline stage updater
│   │   ├── students.html      # Registered student candidate directory
│   │   ├── student_detail.html # Detailed candidate background inspection
│   │   └── settings.html      # Non-sensitive operational diagnostics
│   └── errors/
│       ├── 404.html           # Page not found
│       ├── 403.html           # Access denied
│       └── 500.html           # Server error
│
├── static/
│   ├── css/
│   │   └── style.css          # Production SaaS design system stylesheet
│   └── js/
│       └── main.js           # Client validation, mobile menu, confirm dialogs
│
├── uploads/                   # Local secure document directory
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables configuration template
├── .env                       # Local environment file (git-ignored)
├── .gitignore                 # Standard exclusions (.venv, .env, *.db, uploads/)
└── README.md                  # Platform documentation
```

---

## ⚡ Local Setup & Execution

### 1. Prerequisites
- Python 3.12+ installed.

### 2. Environment Activation
```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
Initialize the database schema and populate sample internship postings:
```bash
python init_db.py
```
*(Optional: Before deploying to production, run `python init_db.py --clear-sample-data` to purge sample listings.)*

### 5. Create Administrator Account
InternTrack does not include pre-seeded default passwords. Create your administrator account securely:
```bash
python create_admin.py
```
You will be prompted to enter your administrator name, email, and a secure password.

### 6. Start the Web Server
```bash
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🧪 Automated Testing

An automated test suite (`test_app.py`) verifies all authentication boundaries, file upload validations, database transactions, role authorization, and diagnostics security.

Run the test suite:
```bash
python -m unittest test_app.py -v
```

**Test Verification Highlights:**
- Public pages & branding verification: **PASSED**
- Candidate registration & duplicate prevention: **PASSED**
- Session authentication & invalid credential rejection: **PASSED**
- Role authorization boundaries (blocking unauthorized access): **PASSED**
- Multi-parameter marketplace search & filtering: **PASSED**
- Resume file validation & duplicate application blocking: **PASSED**
- Profile strength calculation & master resume management: **PASSED**
- Position management (CRUD & visibility toggles): **PASSED**
- 5-stage recruitment pipeline updates: **PASSED**
- Student directory & settings diagnostics without secret leakage: **PASSED**

---

## ☁️ Cloud Architecture & Deployment Roadmap

InternTrack is architected to transition to cloud infrastructure without application rewrites:

1. **Relational Database (Amazon RDS MySQL):**
   - Set `DB_TYPE=mysql` and configure standard database credentials in `.env`.
   - Run `python init_db.py` to auto-provision the MySQL schema.

2. **Document Storage (Amazon S3):**
   - Set `STORAGE_TYPE=s3` and specify `AWS_S3_BUCKET_NAME` and `AWS_REGION` in `.env`.
   - When running on Amazon EC2, attach an IAM instance profile to grant least-privilege bucket access without static keys.

3. **Compute & Reverse Proxy (Amazon EC2):**
   - Deploy behind Gunicorn and Nginx with TLS termination.
   - Attach CloudWatch for real-time monitoring and log management.
