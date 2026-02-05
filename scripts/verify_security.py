"""
Security verification script.
Run: python scripts/verify_security.py
"""
import os
import re
import sys

# Run from faculty_pipeline directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
os.chdir(APP_DIR)


def check_security():
    issues = []

    # 1. Check for hardcoded API keys
    print("Checking for hardcoded API keys...")
    dangerous_patterns = [
        (r'BRAVE_API_KEY\s*=\s*["\'][^"\']+["\']', "BRAVE_API_KEY"),
        (r'SECRET_KEY\s*=\s*["\'][^"\']{20,}["\']', "SECRET_KEY"),
        (r'api_key\s*=\s*["\'][A-Za-z0-9]{20,}["\']', "api_key"),
    ]
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "venv", ".venv", ".git", "__pycache__")]
        for file in files:
            if file.endswith((".py", ".js")) and ".env" not in root:
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", errors="ignore") as f:
                        content = f.read()
                    for pattern, name in dangerous_patterns:
                        if re.search(pattern, content):
                            issues.append(f"Potential hardcoded key ({name}) in {filepath}")
                except Exception:
                    pass

    # 2. Check password hashing
    print("Checking password hashing...")
    try:
        with open("app.py", "r") as f:
            app_content = f.read()
        if "generate_password_hash" not in app_content or "pbkdf2" not in app_content:
            issues.append("app.py: Ensure passwords use generate_password_hash(..., method='pbkdf2:sha256')")
        if "password_hash = password" in app_content or "user.password =" in app_content:
            issues.append("app.py: Never store plain text password")
    except FileNotFoundError:
        issues.append("app.py not found (run from faculty_pipeline/)")

    # 3. Check SECRET_KEY
    print("Checking SECRET_KEY...")
    secret_key = os.environ.get("SECRET_KEY", "")
    if not secret_key or secret_key == "dev" or "dev-secret" in secret_key or len(secret_key) < 32:
        issues.append("SECRET_KEY is weak or missing. Set a strong 32+ char key in .env")

    # Report
    print("\n" + "=" * 50)
    if issues:
        print(f"SECURITY ISSUES FOUND: {len(issues)}")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("No obvious security issues found")
    return issues


if __name__ == "__main__":
    check_security()
