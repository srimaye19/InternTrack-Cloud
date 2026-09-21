import os
import sys
import getpass
import argparse
from database import init_db, query_db, execute_db
from auth import hash_password

def create_admin_user(name=None, email=None, password=None):
    """Securely creates or updates an administrator account."""
    init_db()

    # If parameters not provided, prompt interactively
    if not name:
        name = os.getenv('ADMIN_NAME') or input("Enter Administrator Full Name: ").strip()
    if not email:
        email = os.getenv('ADMIN_EMAIL') or input("Enter Administrator Email: ").strip().lower()
    if not password:
        password = os.getenv('ADMIN_PASSWORD')
        if not password:
            while True:
                p1 = getpass.getpass("Enter Administrator Password (min 8 chars): ")
                if len(p1) < 8:
                    print("[!] Password must be at least 8 characters long.")
                    continue
                p2 = getpass.getpass("Confirm Administrator Password: ")
                if p1 != p2:
                    print("[!] Passwords do not match. Please try again.")
                    continue
                password = p1
                break

    if not name or not email or not password:
        print("[!] Error: Name, email, and password are all required.")
        sys.exit(1)

    if len(password) < 8:
        print("[!] Error: Password must be at least 8 characters long.")
        sys.exit(1)

    hashed_pw = hash_password(password)

    # Check if user already exists
    existing = query_db("SELECT id, role FROM users WHERE email = ?", (email,), one=True)
    if existing:
        execute_db(
            "UPDATE users SET name = ?, password = ?, role = 'admin', is_active = 1 WHERE email = ?",
            (name, hashed_pw, email)
        )
        print(f"[+] Existing account for '{email}' successfully updated to Administrator role.")
    else:
        execute_db(
            "INSERT INTO users (name, email, password, role, is_active) VALUES (?, ?, ?, 'admin', 1)",
            (name, email, hashed_pw)
        )
        print(f"[+] Administrator account '{email}' successfully created.")

def main():
    parser = argparse.ArgumentParser(description="Create or update an InternTrack Administrator account.")
    parser.add_argument("--name", help="Admin Full Name")
    parser.add_argument("--email", help="Admin Email Address")
    parser.add_argument("--password", help="Admin Password (or will be prompted securely)")
    args = parser.parse_args()

    create_admin_user(args.name, args.email, args.password)

if __name__ == '__main__':
    main()
