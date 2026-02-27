#!/usr/bin/env python3
"""
Utility script to check user account and ALLOWED_USERS configuration
Run this script to verify your email is in the database and in ALLOWED_USERS
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import app components
from app import app, db, User

def check_user_and_auth():
    email = "andrewdou@college.harvard.edu"
    email_lower = email.lower()
    
    print("=" * 60)
    print("USER ACCOUNT & AUTHORIZATION CHECK")
    print("=" * 60)
    print()
    
    with app.app_context():
        # Check database for user
        print(f"1. Checking database for email: {email}")
        user = User.query.filter_by(email=email_lower).first()
        
        if user:
            print(f"   ✅ User found in database!")
            print(f"      Email: {user.email}")
            print(f"      Username: {user.username}")
            print(f"      User ID: {user.id}")
            print(f"      Created: {user.created_at}")
        else:
            print(f"   ❌ User NOT found with email: {email}")
            print(f"   Trying to find similar emails...")
            # Try case variations
            all_users = User.query.all()
            matching = [u for u in all_users if email_lower in u.email.lower()]
            if matching:
                print(f"   Found {len(matching)} similar email(s):")
                for u in matching:
                    print(f"      - {u.email} (username: {u.username})")
            else:
                print(f"   No similar emails found.")
                print(f"   Total users in database: {len(all_users)}")
                if len(all_users) <= 20:
                    print(f"   All emails in database:")
                    for u in all_users:
                        print(f"      - {u.email}")
        print()
        
        # Check ALLOWED_USERS
        print("2. Checking ALLOWED_USERS environment variable")
        allowed_users = os.getenv("ALLOWED_USERS", "").strip()
        
        if not allowed_users:
            print("   ⚠️  ALLOWED_USERS is NOT SET")
            print("   → Site is currently PUBLIC (anyone can access)")
        else:
            print(f"   ALLOWED_USERS value: {allowed_users}")
            # Parse emails
            emails = [e.strip().lower() for e in allowed_users.split(",") if e.strip()]
            print(f"   Parsed {len(emails)} authorized email(s):")
            for e in emails:
                print(f"      - {e}")
            print()
            
            # Check if user email is in list
            email_normalized = email_lower.strip()
            if email_normalized in emails:
                print(f"   ✅ Your email ({email}) IS in the authorized list!")
            else:
                print(f"   ❌ Your email ({email}) is NOT in the authorized list!")
                print(f"   Normalized email we're checking: '{email_normalized}'")
                print(f"   Make sure your email in ALLOWED_USERS matches exactly (case-insensitive)")
        print()
        
        # Summary
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)
        if user:
            if allowed_users:
                email_normalized = email_lower.strip()
                emails = [e.strip().lower() for e in allowed_users.split(",") if e.strip()]
                if email_normalized in emails:
                    print("✅ Your account exists and is authorized!")
                    print("   If you can't log in, the issue might be:")
                    print("   1. Wrong password")
                    print("   2. Email format mismatch (check exact email in database above)")
                else:
                    print("❌ Your account exists but is NOT authorized!")
                    print(f"   Add this exact email to ALLOWED_USERS: {user.email}")
            else:
                print("✅ Your account exists and site is public (no restrictions)")
        else:
            print("❌ Your account does NOT exist in the database!")
            print("   You need to sign up first, or check if you used a different email.")
        print("=" * 60)

if __name__ == "__main__":
    try:
        check_user_and_auth()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

