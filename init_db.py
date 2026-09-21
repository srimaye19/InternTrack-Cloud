import os
import sys
import argparse
from config import Config
from database import init_db, query_db, execute_db

def seed_sample_internships():
    """Seeds realistic sample internship listings marked with is_sample=1 for development."""
    sample_internships = [
        (
            "Cloud Infrastructure Engineer Intern",
            "CloudScale Systems",
            "Assist in architecting, automating, and monitoring resilient cloud infrastructure and CI/CD pipelines.",
            "- Build and maintain automated deployment pipelines with GitHub Actions.\n- Implement infrastructure-as-code templates using Terraform.\n- Assist with container orchestration and health monitoring.",
            "Python, Linux, Docker, Cloud Platforms (AWS/GCP/Azure)",
            "Kubernetes, Terraform, CI/CD, Bash scripting",
            "San Jose, CA (Hybrid)",
            "Hybrid",
            "Python, Docker, Linux, Cloud Architecture",
            "3 Months",
            "2026-11-15",
            1
        ),
        (
            "Backend Software Engineer Intern",
            "NextGen Platforms",
            "Design, test, and maintain high-performance RESTful APIs and database schemas for web applications.",
            "- Develop robust API endpoints using Python and Flask.\n- Write unit and integration test suites.\n- Optimize SQL database queries and schema performance.",
            "Python, SQL, REST APIs, Git",
            "Flask, PostgreSQL, Redis, Docker",
            "Austin, TX",
            "On-site",
            "Python, Flask, SQL, REST APIs, Git",
            "6 Months",
            "2026-12-01",
            1
        ),
        (
            "Cloud Security & Compliance Intern",
            "Apex CyberSecurity",
            "Work alongside enterprise security engineers to audit cloud access permissions, analyze logs, and harden network perimeters.",
            "- Audit IAM permissions and implement principle of least privilege.\n- Analyze security logs and configure proactive alerting.\n- Assist in security compliance audits and documentation.",
            "Network Fundamentals, Linux, Security Principles, Python",
            "CloudWatch, IAM, SIEM tools, Bash",
            "Remote",
            "Remote",
            "Cloud Security, IAM, Linux, Networking",
            "3 Months",
            "2026-10-31",
            1
        ),
        (
            "Full-Stack Web Developer Intern",
            "OmniTech Labs",
            "Contribute to modern responsive user interfaces and backend integrations for customer-facing SaaS applications.",
            "- Build accessible and mobile-first frontend interfaces.\n- Connect UI components to backend endpoints.\n- Participate in code reviews and sprint planning.",
            "HTML5, CSS3, JavaScript, Python",
            "Flask, React/Vue, Tailwind CSS, PostgreSQL",
            "Remote",
            "Remote",
            "JavaScript, HTML/CSS, Python, REST APIs",
            "4 Months",
            "2026-11-30",
            1
        ),
        (
            "Data Engineering & Analytics Intern",
            "DataWave Analytics",
            "Design and optimize automated data ingestion pipelines and database transformations.",
            "- Build and maintain ETL pipelines for relational and unstructured data.\n- Write efficient SQL queries and analytical reports.\n- Monitor pipeline performance and data quality checks.",
            "Python, SQL, Data Modeling",
            "Pandas, PySpark, Cloud Data Warehouses",
            "New York, NY",
            "Hybrid",
            "Python, SQL, Data Pipelines, Analytics",
            "6 Months",
            "2026-12-15",
            1
        )
    ]

    for title, company, desc, resp, req_skills, pref_skills, loc, itype, skills, duration, deadline, is_sample in sample_internships:
        existing = query_db(
            "SELECT id FROM internships WHERE title = ? AND company = ?",
            (title, company),
            one=True
        )
        if not existing:
            execute_db(
                """INSERT INTO internships 
                   (title, company, description, responsibilities, required_skills, preferred_skills,
                    location, internship_type, skills, duration, deadline, is_active, is_sample) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)""",
                (title, company, desc, resp, req_skills, pref_skills, loc, itype, skills, duration, deadline, is_sample)
            )
            print(f"[+] Added sample internship: {title} at {company}")

def clear_sample_data():
    """Removes all sample data prior to production deployment."""
    _, deleted_count = execute_db("DELETE FROM internships WHERE is_sample = 1")
    print(f"[*] Cleared {deleted_count} sample internship listing(s).")

def main():
    parser = argparse.ArgumentParser(description="InternTrack Database Setup & Sample Data Utility")
    parser.add_argument("--clear-sample-data", action="store_true", help="Remove all sample internship postings")
    parser.add_argument("--seed-samples", action="store_true", help="Seed sample internship postings")
    args = parser.parse_args()

    print(f"[*] Initializing database schema (Engine: {Config.DB_TYPE})...")
    init_db()
    print("[+] Database schema verified and updated.")

    if args.clear_sample_data:
        clear_sample_data()
        return

    # By default, seed sample internships for local development
    print("[*] Seeding sample internship listings for development/testing...")
    seed_sample_internships()
    print("\n[i] Note: No default user accounts were created.")
    print("[i] Run 'python create_admin.py' to set up your administrator account.")
    print("[*] Initialization complete.")

if __name__ == '__main__':
    main()
