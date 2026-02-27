#!/usr/bin/env python3
"""
Admin utility to reset a user's password
Usage: python reset_password_admin.py <email> <new_password>
"""
import sys
import os
from dotenv import load_dotenv

load_dotenv()

from app import app, db, User

def reset_password(email, new_password):
    """Reset password for a user by email."""
    with app.app_context():
        email_lower = email.lower().strip()
        user = User.query.filter_by(email=email_lower).first()
        
        if not user:
            print(f"❌ User not found with email: {email}")
            # Try to find similar
            all_users = User.query.all()
            matching = [u for u in all_users if email_lower in u.email.lower()]
            if matching:
                print(f"\nFound {len(matching)} similar email(s):")
                for u in matching:
                    print(f"  - {u.email} (username: {u.username})")
            return False
        
        # Reset password
        user.set_password(new_password)
        db.session.commit()
        
        print(f"✅ Password reset successful!")
        print(f"   Email: {user.email}")
        print(f"   Username: {user.username}")
        print(f"   New password: {new_password}")
        print(f"\nYou can now log in with this password.")
        return True

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_password_admin.py <email> <new_password>")
        print("Example: python reset_password_admin.py andrewdou@college.harvard.edu mynewpassword")
        sys.exit(1)
    
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    if len(new_password) < 6:
        print("❌ Password must be at least 6 characters long")
        sys.exit(1)
    
    try:
        reset_password(email, new_password)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

