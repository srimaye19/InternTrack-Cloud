import os
import sqlite3
from config import Config

def get_db_connection():
    """Returns a database connection based on Config.DB_TYPE."""
    if Config.DB_TYPE == 'mysql':
        import pymysql
        import pymysql.cursors
        connection = pymysql.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )
        return connection
    else:
        # Default: SQLite
        connection = sqlite3.connect(Config.SQLITE_DB_PATH)
        connection.row_factory = sqlite3.Row
        # Enable foreign key constraint support in SQLite
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

def query_db(query, args=(), one=False):
    """
    Executes a SELECT query using parameterized arguments.
    Standardized query syntax uses '?' placeholders.
    Returns dictionaries for rows.
    """
    conn = get_db_connection()
    try:
        if Config.DB_TYPE == 'mysql':
            mysql_query = query.replace('?', '%s')
            with conn.cursor() as cursor:
                cursor.execute(mysql_query, args)
                rows = cursor.fetchall()
        else:
            cur = conn.cursor()
            cur.execute(query, args)
            rows = [dict(row) for row in cur.fetchall()]

        if one:
            return rows[0] if rows else None
        return rows
    finally:
        conn.close()

def execute_db(query, args=()):
    """
    Executes an INSERT, UPDATE, or DELETE query with parameterized arguments.
    Standardized query syntax uses '?' placeholders.
    Returns the last inserted id and the number of affected rows.
    """
    conn = get_db_connection()
    try:
        if Config.DB_TYPE == 'mysql':
            mysql_query = query.replace('?', '%s')
            with conn.cursor() as cursor:
                cursor.execute(mysql_query, args)
                last_id = cursor.lastrowid
                row_count = cursor.rowcount
            return last_id, row_count
        else:
            cur = conn.cursor()
            cur.execute(query, args)
            conn.commit()
            last_id = cur.lastrowid
            row_count = cur.rowcount
            return last_id, row_count
    finally:
        conn.close()

def init_db():
    """Initializes tables with proper foreign keys, constraints, and extended schema."""
    conn = get_db_connection()
    try:
        if Config.DB_TYPE == 'mysql':
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(120) NOT NULL,
                    email VARCHAR(120) NOT NULL UNIQUE,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'student',
                    phone VARCHAR(50) DEFAULT NULL,
                    college VARCHAR(150) DEFAULT NULL,
                    degree VARCHAR(100) DEFAULT NULL,
                    graduation_year VARCHAR(10) DEFAULT NULL,
                    skills TEXT DEFAULT NULL,
                    linkedin_url VARCHAR(255) DEFAULT NULL,
                    github_url VARCHAR(255) DEFAULT NULL,
                    resume_filename VARCHAR(255) DEFAULT NULL,
                    is_active INT DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS internships (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(200) NOT NULL,
                    company VARCHAR(150) NOT NULL,
                    description TEXT NOT NULL,
                    responsibilities TEXT DEFAULT NULL,
                    required_skills TEXT DEFAULT NULL,
                    preferred_skills TEXT DEFAULT NULL,
                    location VARCHAR(150) NOT NULL,
                    internship_type VARCHAR(50) NOT NULL DEFAULT 'Remote',
                    skills VARCHAR(255) NOT NULL,
                    duration VARCHAR(100) NOT NULL,
                    deadline VARCHAR(50) NOT NULL,
                    is_active INT DEFAULT 1,
                    is_sample INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT NOT NULL,
                    internship_id INT NOT NULL,
                    resume_filename VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'Applied',
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT fk_student FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
                    CONSTRAINT fk_internship FOREIGN KEY (internship_id) REFERENCES internships(id) ON DELETE CASCADE,
                    CONSTRAINT uq_student_internship UNIQUE (student_id, internship_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
        else:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'student',
                    phone TEXT,
                    college TEXT,
                    degree TEXT,
                    graduation_year TEXT,
                    skills TEXT,
                    linkedin_url TEXT,
                    github_url TEXT,
                    resume_filename TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS internships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    description TEXT NOT NULL,
                    responsibilities TEXT,
                    required_skills TEXT,
                    preferred_skills TEXT,
                    location TEXT NOT NULL,
                    internship_type TEXT NOT NULL DEFAULT 'Remote',
                    skills TEXT NOT NULL,
                    duration TEXT NOT NULL,
                    deadline TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    is_sample INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    internship_id INTEGER NOT NULL,
                    resume_filename TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Applied',
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (internship_id) REFERENCES internships(id) ON DELETE CASCADE,
                    UNIQUE(student_id, internship_id)
                );
            """)
            conn.commit()

            # Safe column migration check for existing SQLite databases
            _migrate_sqlite_columns(conn)
    finally:
        conn.close()

def _migrate_sqlite_columns(conn):
    """Safely adds missing columns if upgrading an existing SQLite database."""
    cur = conn.cursor()
    
    # Check users table columns
    cur.execute("PRAGMA table_info(users)")
    user_cols = [row[1] for row in cur.fetchall()]
    new_user_cols = [
        ('phone', 'TEXT'),
        ('college', 'TEXT'),
        ('degree', 'TEXT'),
        ('graduation_year', 'TEXT'),
        ('skills', 'TEXT'),
        ('linkedin_url', 'TEXT'),
        ('github_url', 'TEXT'),
        ('resume_filename', 'TEXT'),
        ('is_active', 'INTEGER DEFAULT 1')
    ]
    for col_name, col_type in new_user_cols:
        if col_name not in user_cols:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")

    # Check internships table columns
    cur.execute("PRAGMA table_info(internships)")
    internship_cols = [row[1] for row in cur.fetchall()]
    new_internship_cols = [
        ('responsibilities', 'TEXT'),
        ('required_skills', 'TEXT'),
        ('preferred_skills', 'TEXT'),
        ('internship_type', "TEXT NOT NULL DEFAULT 'Remote'"),
        ('is_active', 'INTEGER DEFAULT 1'),
        ('is_sample', 'INTEGER DEFAULT 0')
    ]
    for col_name, col_type in new_internship_cols:
        if col_name not in internship_cols:
            cur.execute(f"ALTER TABLE internships ADD COLUMN {col_name} {col_type}")

    conn.commit()
