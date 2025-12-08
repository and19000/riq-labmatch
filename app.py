# Import all the libraries we need for the app
import os
import json
import re
import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor, as_completed

# Flask handles our web server and routing
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
# SQLAlchemy helps us work with the database
from flask_sqlalchemy import SQLAlchemy
# Werkzeug provides password hashing and file security
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
# OpenAI API for AI-powered features like email drafting and lab matching
from openai import OpenAI
# Load environment variables from .env file (keeps API keys secret)
from dotenv import load_dotenv

# Load our environment variables (like API keys) from the .env file
load_dotenv()
# Set up the OpenAI client so we can use their AI models
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# We use gpt-4o-mini because it's cost-effective and still very capable
GPT_MODEL = "gpt-4o-mini"

# Create our Flask application
app = Flask(__name__)

# This secret key is used to encrypt session data (like keeping users logged in)
# In production, this should be a long random string stored securely
app.config["SECRET_KEY"] = "dev-secret-change-later"

# Set up our database - we're using SQLite which stores everything in a local file
# The database file will be created in the project root as riq.db
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///riq.db"
# We don't need SQLAlchemy to track every change, so we disable this for performance
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Create the database connection object
db = SQLAlchemy(app)

# Database Models - these define the structure of our data tables

# The User model stores information about people who sign up for accounts
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    # We never store passwords in plain text - only the hashed version
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # When a user sets their password, we hash it before storing
    # We use pbkdf2:sha256 because it works with Python 3.9 (scrypt needs Python 3.10+)
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    # Check if a provided password matches the stored hash
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

# SavedPI tracks which Principal Investigators (PIs) each user has saved
class SavedPI(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pi_id = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Make sure a user can't save the same PI twice
    __table_args__ = (
        db.UniqueConstraint("user_id", "pi_id", name="uq_user_pi"),
    )

# Resume stores information about uploaded resume files
class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    # We extract text from the resume so the AI can analyze it for matching
    resume_text = db.Column(db.Text)

# UserProfile stores additional information about users (like their major, what they're looking for, etc.)
class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    major_field = db.Column(db.String(255))
    # What year they're in school (first year, sophomore, junior, senior, masters student, graduate student, other)
    year_in_school = db.Column(db.String(50))
    # What kind of opportunity they're seeking (thesis lab, summer RA, rotation, gap year, in term research, exploring)
    # Stored as comma-separated values
    looking_for = db.Column(db.String(500))
    # Their top techniques of interest (stored as JSON array or comma-separated)
    top_techniques = db.Column(db.Text)
    onboarding_complete = db.Column(db.Boolean, default=False)
    # Track how complete their profile is (0-100%)
    profile_completeness = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# PasswordResetToken stores temporary tokens for password reset requests
# These tokens expire after 1 hour for security
class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    # Check if the token is still valid (not expired and not used)
    def is_valid(self):
        return not self.used and datetime.utcnow() < self.expires_at

# Configuration for file uploads
UPLOAD_FOLDER = "uploads"
# Only allow PDF and DOCX files for resumes
ALLOWED_EXTENSIONS = {"pdf", "docx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Make sure the uploads folder exists so we can save files there
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database - this function creates tables and handles migrations
def init_db():
    """Initialize database and run migrations."""
    with app.app_context():
        db.create_all()
        
        # Run migrations for existing tables
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            
            # Migration: Add username column to User table if it doesn't exist
            if 'user' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('user')]
                
                if 'username' not in columns:
                    # Add username column using raw SQL
                    # SQLite supports ADD COLUMN in ALTER TABLE
                    with db.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE user ADD COLUMN username VARCHAR(80)"))
                    print("Migration: Added username column to user table")
            
            # Migration: Add year_in_school column to user_profile table if it doesn't exist
            if 'user_profile' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('user_profile')]
                
                if 'year_in_school' not in columns:
                    with db.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE user_profile ADD COLUMN year_in_school VARCHAR(50)"))
                    print("Migration: Added year_in_school column to user_profile table")
                
                # Migration: Update looking_for column size if it's still 255
                # Check the column type - SQLite doesn't enforce VARCHAR lengths, but we update for consistency
                # Since SQLite stores everything as TEXT, we'll just ensure the column exists with proper size
                # The model definition will handle the size going forward
                
        except Exception as e:
            # If table doesn't exist yet, create_all will handle it
            # Or if migration fails, continue anyway
            print(f"Migration check: {e}")

# Initialize the database when the app starts
init_db()

# Set up paths to our data files
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FACULTY_PATH = os.path.join(DATA_DIR, "faculty.json")

# Helper Functions - these do common tasks we need throughout the app

def load_faculty():
    """Load all the faculty/PI data from our JSON file."""
    with open(FACULTY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_faculty_by_id(pi_id: str):
    """Find and return a specific PI by their ID, or None if not found."""
    all_faculty = load_faculty()
    for pi in all_faculty:
        if pi["id"] == pi_id:
            return pi
    return None

def allowed_file(filename: str) -> bool:
    """Check if a filename has an allowed extension (PDF or DOCX)."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# Email Helper Functions - for sending password reset emails

def send_password_reset_email(user_email: str, reset_token: str, base_url: str = None) -> bool:
    """
    Send a password reset email to the user.
    This function uses SMTP to send emails. You'll need to configure SMTP settings in your .env file.
    
    Args:
        user_email: The email address to send the reset link to
        reset_token: The secure token for password reset
        base_url: The base URL of the application (for creating the reset link)
    
    Returns True if email was sent successfully, False otherwise.
    """
    try:
        # Get the base URL - use the one provided or try to get it from Flask request context
        if not base_url:
            try:
                base_url = request.url_root
            except RuntimeError:
                # If we're not in a request context, use localhost as default
                base_url = "http://localhost:5001/"
        
        # Get email configuration from environment variables
        # For development, you can use Gmail SMTP or another email service
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_username = os.getenv("SMTP_USERNAME", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        from_email = os.getenv("FROM_EMAIL", smtp_username)
        
        # Create the reset link
        reset_link = f"{base_url}reset-password/{reset_token}"
        
        # If SMTP credentials aren't configured, we can't send emails
        # In development, we'll just print the reset link instead
        if not smtp_username or not smtp_password:
            print(f"\n{'='*60}")
            print("PASSWORD RESET EMAIL (SMTP not configured - showing link here):")
            print(f"To: {user_email}")
            print(f"Reset Link: {reset_link}")
            print(f"{'='*60}\n")
            return True  # Return True so the user flow continues
        
        # Create the email message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = user_email
        msg['Subject'] = "RIQ Lab Matcher - Password Reset Request"
        
        # Email body with the reset link
        body = f"""
Hello,

You requested to reset your password for your RIQ Lab Matcher account.

Click the link below to reset your password:
{reset_link}

This link will expire in 1 hour.

If you didn't request this password reset, please ignore this email.

Best regards,
RIQ Lab Matcher Team
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server and send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Enable encryption
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        # If email sending fails, log the error but don't break the flow
        print(f"Error sending password reset email: {str(e)}")
        # In development, still show the link
        print(f"\nPassword reset link: {request.url_root}reset-password/{reset_token}\n")
        return False


# This function processes a batch of faculty members in parallel for faster matching
# Instead of checking all labs one by one, we split them into batches and process multiple batches at once
def process_faculty_batch(faculty_batch, resume_info, batch_num, total_batches):
    """Process a batch of faculty members and return match scores using AI."""
    try:
        # Create concise summaries for this batch (optimized for speed)
        # We use a more compact format to reduce token count and processing time
        faculty_summaries = []
        for pi in faculty_batch:
            # More concise format to reduce token count and processing time
            summary = f"{pi['name']} ({pi['id']}): {pi['research_areas']}"
            if pi.get('lab_techniques'):
                summary += f" | Techniques: {pi['lab_techniques'][:100]}"  # Truncate long technique lists
            summary += f" | {pi['department']}, {pi['school']}"
            faculty_summaries.append(summary)
        
        faculty_text = "\n".join(faculty_summaries)
        
        # Build the prompt we'll send to the AI - optimized for faster processing
        # This tells the AI what we want it to do and how to score matches
        prompt = f"""Match student resume with compatible labs. Return JSON array only.

STUDENT: {resume_info[:500]}

LABS (Batch {batch_num + 1}/{total_batches}):
{faculty_text}

Scoring (40% research match, 25% skills, 15% level, 10% dept, 10% impact):
- 90-100: Exceptional | 80-89: Excellent | 70-79: Good | 60-69: Moderate | 50-59: Weak | <50: Exclude

Return JSON array: [{{"pi_id": "id", "score": 85, "reason": "brief reason"}}]
Only include labs with score >= 50. Rank highest to lowest."""

        # Send the prompt to OpenAI and get back match scores
        # We use a low temperature (0.2) to get more consistent, reliable results
        # The OpenAI client handles timeouts internally, and we limit tokens for faster processing
        completion = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a lab matching algorithm. Return only valid JSON arrays, no markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000,  # Limit response length for faster processing
        )
        
        response_text = completion.choices[0].message.content
        
        # The AI might return JSON in different formats, so we try to extract it
        # First, look for a JSON array in the response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            try:
                matches_data = json.loads(json_match.group())
                return matches_data
            except json.JSONDecodeError:
                # Sometimes the AI wraps it in an object, so try that too
                try:
                    full_json = json.loads(response_text)
                    if 'matches' in full_json:
                        return full_json['matches']
                    elif isinstance(full_json, list):
                        return full_json
                    else:
                        return []
                except:
                    return []
        else:
            return []
            
    except Exception as e:
        # If something goes wrong, just return an empty list
        # The caller will handle this gracefully
        print(f"Error processing batch {batch_num + 1}: {str(e)}")
        return []


# Routes - these define what happens when users visit different pages

@app.route("/test-gpt")
def test_gpt():
    """Simple test route to make sure OpenAI API is working correctly."""
    try:
        completion = client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a friendly assistant."},
                {"role": "user", "content": "Say hi in one short sentence."}
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error calling OpenAI: {e}"


@app.route("/")
def index():
    """Show the homepage with the hero section and feature cards."""
    return render_template("index.html")


@app.route("/general")
def general():
    """Show the browse labs page where users can filter and search through all available PIs."""
    # Get any filter selections from the URL (like ?school=MIT&department=Biology)
    selected_school = request.args.get("school", "").strip()
    selected_department = request.args.get("department", "").strip()
    selected_technique = request.args.get("technique", "").strip()
    selected_location = request.args.get("location", "").strip()

    all_faculty = load_faculty()

    # Build lists of unique values for the filter dropdowns
    # This lets users see all available options
    schools = sorted(set(pi["school"] for pi in all_faculty))
    departments = sorted(set(pi["department"] for pi in all_faculty))
    
    # Extract all unique lab techniques and locations from the data
    # Techniques are stored as comma-separated strings, so we need to split them
    all_techniques = set()
    all_locations = set()
    for pi in all_faculty:
        if pi.get("lab_techniques"):
            techniques = [t.strip() for t in pi["lab_techniques"].split(",")]
            all_techniques.update(techniques)
        if pi.get("specific_location"):
            all_locations.add(pi["specific_location"])
        else:
            all_locations.add(pi["location"])
    
    techniques = sorted(all_techniques)
    locations = sorted(all_locations)

    # Filter the faculty list based on what the user selected
    filtered = []
    for pi in all_faculty:
        # Skip this PI if it doesn't match the selected school
        if selected_school and pi["school"] != selected_school:
            continue
        # Skip if it doesn't match the selected department
        if selected_department and pi["department"] != selected_department:
            continue
        # Check if the selected technique is in this PI's techniques list
        if selected_technique:
            pi_techniques = [t.strip().lower() for t in (pi.get("lab_techniques", "") or "").split(",")]
            if selected_technique.lower() not in pi_techniques:
                continue
        # Check location match
        if selected_location:
            pi_location = pi.get("specific_location", pi["location"])
            if selected_location not in pi_location:
                continue
        # If we made it here, this PI matches all the filters
        filtered.append(pi)

    # Check which PIs the current user has already saved
    # This lets us show a "Saved" indicator instead of a "Save" button
    saved_pi_ids = set()
    user_id = session.get("user_id")
    if user_id:
        saved_rows = SavedPI.query.filter_by(user_id=user_id).all()
        saved_pi_ids = {row.pi_id for row in saved_rows}

    return render_template(
        "general.html",
        faculty_list=filtered,
        selected_school=selected_school,
        selected_department=selected_department,
        selected_technique=selected_technique,
        selected_location=selected_location,
        schools=schools,
        departments=departments,
        techniques=techniques,
        locations=locations,
        saved_pi_ids=saved_pi_ids,
    )

@app.route("/matches")
def matches():
    """Show AI-ranked lab matches based on the user's resume. This is the core feature!"""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    # Allow demo mode so people can try it without uploading a resume
    use_demo = request.args.get("demo") == "true"
    
    # Get the user's most recent resume upload
    resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    
    if not resume and not use_demo:
        flash("Please upload a resume first to see your matches.", "info")
        return redirect(url_for("resume_upload"))
    
    all_faculty = load_faculty()
    
    # Prepare the resume information to send to the AI
    # If demo mode, use a sample resume; otherwise use the actual uploaded resume text
    if use_demo:
        resume_info = """Computer Science major with strong background in machine learning and neuroscience. 
        Research experience: 2 years in computational neuroscience lab working with neural networks and electrophysiology data.
        Skills: Python, PyTorch, MATLAB, data analysis, statistical modeling.
        Interests: Computational neuroscience, brain-computer interfaces, AI applications in healthcare.
        Publications: 1 first-author paper in preparation on neural decoding algorithms."""
    else:
        resume_info = resume.resume_text if resume.resume_text else 'Resume uploaded but text extraction pending. Analyze based on filename and typical student profile.'
    
    # Use parallel batch processing to speed up matching
    # Instead of checking labs one by one (which would be very slow), we split them into batches
    # and process multiple batches at the same time using multiple threads
    try:
        # Split faculty into batches for parallel processing
        # Smaller batches = more parallelism, faster overall
        # We use batches of 10 labs each, processing up to 100 labs total for optimal speed
        BATCH_SIZE = 10  # Reduced from 15 for more parallel requests
        faculty_to_process = all_faculty[:100]  # Process top 100 labs (reduced from 150 for speed)
        batches = [faculty_to_process[i:i + BATCH_SIZE] for i in range(0, len(faculty_to_process), BATCH_SIZE)]
        total_batches = len(batches)
        
        # Process batches in parallel using ThreadPoolExecutor
        # This is what makes it 10x faster than processing sequentially
        # We use 20 workers for maximum parallelism
        all_matches_data = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Submit all batch processing tasks to run in parallel
            future_to_batch = {
                executor.submit(process_faculty_batch, batch, resume_info, idx, total_batches): idx 
                for idx, batch in enumerate(batches)
            }
            
            # Collect results as they complete (they might finish in any order)
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_results = future.result()
                    if batch_results:
                        all_matches_data.extend(batch_results)
                except Exception as e:
                    print(f"Error in batch {batch_idx + 1}: {str(e)}")
                    # Continue processing other batches even if one fails
        
        matches_data = all_matches_data
            
    except Exception as e:
        # If something goes wrong with the AI, show all labs without ranking
        # This way the user still gets results even if the AI is having issues
        matches_data = [{"pi_id": pi["id"], "score": 50, "reason": "Unable to generate match score"} for pi in all_faculty]
        flash(f"AI matching temporarily unavailable. Showing all labs. Error: {str(e)}", "warning")
    
    # Combine the match scores with the full PI data
    pi_by_id = {pi["id"]: pi for pi in all_faculty}
    ranked_matches = []
    
    for match in matches_data:
        pi_id = match.get("pi_id")
        if pi_id in pi_by_id:
            pi = pi_by_id[pi_id].copy()
            pi["match_score"] = match.get("score", 50)
            pi["match_reason"] = match.get("reason", "Match found")
            ranked_matches.append(pi)
    
    # Sort by match score from highest to lowest
    ranked_matches.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    
    # Check which PIs the user has already saved
    saved_pi_ids = set()
    saved_rows = SavedPI.query.filter_by(user_id=user_id).all()
    saved_pi_ids = {row.pi_id for row in saved_rows}
    
    return render_template(
        "matches.html",
        matches=ranked_matches,
        saved_pi_ids=saved_pi_ids,
        has_resume=True
    )

@app.route("/save-pi/<pi_id>", methods=["POST"])
def save_pi(pi_id):
    """Save a PI to the user's saved list. This is called when they click the 'Save' button."""
    user_id = session.get("user_id")
    if not user_id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": False, "error": "Not logged in"}), 401
        return redirect(url_for("login"))

    # Check if they've already saved this PI (avoid duplicates)
    # The database has a unique constraint too, but we check here to avoid errors
    existing = SavedPI.query.filter_by(user_id=user_id, pi_id=pi_id).first()
    if existing is None:
        saved = SavedPI(user_id=user_id, pi_id=pi_id)
        db.session.add(saved)
        db.session.commit()
        saved_status = True
    else:
        saved_status = False  # Already saved

    # Return JSON for AJAX requests (used by the save button JavaScript), otherwise redirect
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "already_saved": not saved_status})
    
    # Fallback for non-AJAX requests - send them back to wherever they came from
    return redirect(request.referrer or url_for("saved_pis"))


@app.route("/resume", methods=["GET", "POST"])
def resume_upload():
    """Handle resume uploads. Users need to upload a resume to get AI-powered matches."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        # Make sure the form actually included a file
        if "resume" not in request.files:
            error = "No file part in the form."
            return render_template("resume_upload.html", error=error)

        file = request.files["resume"]

        # Check if they actually selected a file (not just submitted empty form)
        if file.filename == "":
            error = "No file selected."
            return render_template("resume_upload.html", error=error)

        # Validate the file type and save it
        if file and allowed_file(file.filename):
            # Make the filename safe (remove any dangerous characters)
            filename = secure_filename(file.filename)
            # Add user_id to the filename so multiple users can upload files with the same name
            user_filename = f"{user_id}_{filename}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], user_filename)
            file.save(save_path)
            
            # Extract text from the resume for AI analysis
            # Note: This is a placeholder - in production you'd use libraries like PyPDF2 or python-docx
            # to actually extract the text from PDFs and Word documents
            resume_text = ""  # Placeholder - would extract actual text here
            
            # Save the resume record to the database
            resume = Resume(
                user_id=user_id,
                filename=filename,
                file_path=save_path,
                resume_text=resume_text
            )
            db.session.add(resume)
            db.session.commit()
            
            flash("Resume uploaded successfully! You can now view your matches.", "success")
            return redirect(url_for("matches"))
        else:
            error = "File type not allowed. Please upload a PDF or DOCX."
            return render_template("resume_upload.html", error=error)

    # GET request - just show the upload form and any existing resume
    existing_resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    return render_template("resume_upload.html", existing_resume=existing_resume)


@app.route("/saved")
def saved_pis():
    """Show all the PIs that the user has saved to their list."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # Load all faculty data and create a lookup dictionary
    all_faculty = load_faculty()
    pi_by_id = {pi["id"]: pi for pi in all_faculty}

    # Get all the saved PI IDs for this user
    saved_rows = SavedPI.query.filter_by(user_id=user_id).all()
    # Convert the saved IDs back into full PI data
    saved_pis_data = []
    for row in saved_rows:
        pi = pi_by_id.get(row.pi_id)
        if pi:
            saved_pis_data.append(pi)

    return render_template("saved_pis.html", saved_pis=saved_pis_data)


@app.route("/unsave-pi/<pi_id>", methods=["POST"])
def unsave_pi(pi_id):
    """Remove a PI from the user's saved list."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # Find and delete the saved PI record
    saved = SavedPI.query.filter_by(user_id=user_id, pi_id=pi_id).first()
    if saved:
        db.session.delete(saved)
        db.session.commit()

    return redirect(url_for("saved_pis"))

@app.route("/bulk-email", methods=["GET", "POST"])
def bulk_email():
    """Generate emails for multiple saved PIs at once."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    # Get user's saved PIs
    all_faculty = load_faculty()
    pi_by_id = {pi["id"]: pi for pi in all_faculty}
    saved_rows = SavedPI.query.filter_by(user_id=user_id).all()
    saved_pis_data = [pi_by_id.get(row.pi_id) for row in saved_rows if row.pi_id in pi_by_id]
    
    # Get user info
    user = User.query.get(user_id)
    user_resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    
    if request.method == "POST":
        selected_pi_ids = request.form.getlist("pi_ids")
        student_name = request.form.get("student_name", user.username).strip()
        student_email = request.form.get("student_email", user.email).strip()
        student_background = request.form.get("student_background", "").strip()
        research_interest = request.form.get("research_interest", "").strip()
        
        if not selected_pi_ids:
            flash("Please select at least one PI.", "error")
            return redirect(url_for("bulk_email"))
        
        generated_emails = []
        for pi_id in selected_pi_ids:
            pi = get_faculty_by_id(pi_id)
            if not pi:
                continue
            
            try:
                # Use same enhanced prompt as single email
                resume_context = ""
                if user_resume and user_resume.resume_text:
                    resume_context = f"\nStudent's Resume Summary: {user_resume.resume_text[:500]}"
                
                prompt = f"""Write a professional, personalized cold email to {pi['name']}, {pi['title']} at {pi['department']}, {pi['school']}.

PI INFORMATION:
- Name: {pi['name']}
- Title: {pi['title']}
- Department: {pi['department']}, {pi['school']}
- Research Areas: {pi['research_areas']}
- Location: {pi.get('specific_location', pi['location'])}
- H-index: {pi.get('h_index', 'Not available')}
- Lab Techniques: {pi.get('lab_techniques', 'Not specified')}

STUDENT INFORMATION:
- Name: {student_name}
- Email: {student_email}
- Background: {student_background if student_background else 'Undergraduate/Graduate student'}
- Specific Research Interest: {research_interest if research_interest else f'Interested in {pi["research_areas"]}'}
{resume_context}

Write a professional email (under 250 words) with subject line. Format as:
Subject: [subject line]

Dear Dr. [Last Name],

[email body]

Best regards,
{student_name}"""

                completion = client.chat.completions.create(
                    model=GPT_MODEL,
                    messages=[
                        {"role": "system", "content": "You are an expert at writing professional academic emails. Create personalized, specific emails that show genuine research interest."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                )
                
                email_draft = completion.choices[0].message.content
                generated_emails.append({
                    "pi": pi,
                    "draft": email_draft,
                    "pi_email": pi.get("email", "")
                })
            except Exception as e:
                flash(f"Error generating email for {pi['name']}: {str(e)}", "error")
        
        return render_template("bulk_email_results.html", emails=generated_emails)
    
    return render_template("bulk_email.html", saved_pis=saved_pis_data, user=user)


@app.route("/draft-email", methods=["GET", "POST"])
def draft_email():
    """Generate a personalized email draft to send to a PI. This uses AI to write professional cold emails."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    error = None
    draft = None
    # Get the PI ID from either the URL (if they clicked a link) or the form (if they submitted)
    pi_id = request.args.get("pi_id") or (request.form.get("pi_id") if request.method == "POST" else None)
    pi = None
    
    if pi_id:
        pi = get_faculty_by_id(pi_id)
    
    if request.method == "POST":
        pi_id = request.form.get("pi_id", "").strip()
        student_name = request.form.get("student_name", "").strip()
        student_email = request.form.get("student_email", "").strip()
        student_background = request.form.get("student_background", "").strip()
        research_interest = request.form.get("research_interest", "").strip()
        
        if not pi_id:
            error = "Please select a PI."
        elif not student_name or not student_email:
            error = "Please provide your name and email."
        else:
            pi = get_faculty_by_id(pi_id)
            if not pi:
                error = "PI not found."
            else:
                try:
                    # Get the user's resume to include context in the email
                    user_resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
                    resume_context = ""
                    if user_resume and user_resume.resume_text:
                        # Only include the first 500 characters to keep the prompt manageable
                        resume_context = f"\nStudent's Resume Summary: {user_resume.resume_text[:500]}"
                    
                    # Build a detailed prompt for the AI to generate a personalized email
                    # We include all the PI's information and the student's background
                    # The email should sound natural, human, and conversational - not robotic, overly formal, or edgy
                    prompt = f"""Write a professional, personalized cold email to {pi['name']}, {pi['title']} at {pi['department']}, {pi['school']}. The email should sound natural, human, and conversational - not robotic, overly formal, or edgy.

PI INFORMATION:
- Name: {pi['name']}
- Title: {pi['title']}
- Department: {pi['department']}, {pi['school']}
- Research Areas: {pi['research_areas']}
- Location: {pi.get('specific_location', pi['location'])}
- H-index: {pi.get('h_index', 'Not available')}
- Lab Techniques: {pi.get('lab_techniques', 'Not specified')}
- Website: {pi.get('website', 'N/A')}
- Email: {pi.get('email', 'N/A')}

STUDENT INFORMATION:
- Name: {student_name}
- Email: {student_email}
- Background: {student_background if student_background else 'Undergraduate/Graduate student'}
- Specific Research Interest: {research_interest if research_interest else f'Interested in {pi["research_areas"]}'}
{resume_context}

EMAIL TONE & STYLE (CRITICAL - base on this example):
- Start with a warm, natural greeting like "I hope you're doing well" or "I hope this email finds you well"
- Write conversationally, as if speaking to a mentor, not a corporate executive
- Be specific about what interests you (mention research areas, papers if known, or specific techniques)
- Show genuine interest without being overly enthusiastic or gushing
- Be humble but confident - acknowledge what you don't know while showing willingness to learn
- Mention specific courses, skills, or experiences that are relevant
- Be direct about what you're asking for (research opportunity, joining a project, etc.)
- Keep it professional but warm - avoid corporate jargon or overly formal language
- End naturally with "Thank you for your time and consideration" or similar

EMAIL STRUCTURE:
1. Subject line: Clear and specific (e.g., "Research Opportunity Inquiry - [Your Name]" or "Inquiry About Research Opportunities")
2. Opening: Warm greeting + brief introduction (name, year/level, institution, major/field)
3. Body paragraph 1: Express specific interest in their research - mention specific research areas, papers, or techniques that interest you. Explain why it's meaningful to you.
4. Body paragraph 2: Your relevant background - courses, skills, programming languages, research experience. Mention time commitment if relevant (e.g., "10+ hours per week"). Show you're a determined learner.
5. Closing: Direct but polite request + mention resume if attached + thank you

IMPORTANT GUIDELINES:
- Sound like a real student writing to a professor, not a business email
- Be specific and genuine - avoid generic phrases
- Keep total length around 200-300 words
- Avoid: "I am writing to inquire", "I would like to take this opportunity", overly formal corporate language
- Use: Natural transitions, specific details, genuine interest, conversational tone
- Show you've done your research on their work
- Be authentic and human - write as you would speak to a respected mentor

Format the response as:
Subject: [subject line]

Dear Dr. [Last Name],

[email body - natural, conversational, human tone]

Thank you for your time and consideration,

{student_name}"""

                    completion = client.chat.completions.create(
                        model=GPT_MODEL,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that writes natural, human-sounding academic emails. Write as a real student would write to a professor - conversational, genuine, and authentic. Avoid corporate jargon, overly formal language, or robotic phrasing."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.8,  # Slightly higher temperature for more natural variation
                    )
                    draft = completion.choices[0].message.content
                except Exception as e:
                    error = f"Error generating email draft: {str(e)}"
    
    # Check if this is an AJAX/JSON request (for dynamic email generation)
    wants_json = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        request.headers.get('Accept', '').startswith('application/json') or
        request.args.get('format') == 'json'
    )
    
    if wants_json and request.method == 'POST':
        # Return JSON response for AJAX requests
        if error:
            return jsonify({'success': False, 'error': error}), 400
        elif draft:
            return jsonify({
                'success': True,
                'draft': draft,
                'pi': {
                    'id': pi['id'],
                    'name': pi['name'],
                    'email': pi.get('email', '')
                } if pi else None
            })
        else:
            return jsonify({'success': False, 'error': 'No draft generated'}), 400
    
    # Get saved PIs for dropdown if no PI selected (only show saved PIs, not all faculty)
    saved_pis_data = None
    if not pi:
        all_faculty = load_faculty()
        pi_by_id = {pi["id"]: pi for pi in all_faculty}
        saved_rows = SavedPI.query.filter_by(user_id=user_id).all()
        saved_pis_data = [pi_by_id.get(row.pi_id) for row in saved_rows if row.pi_id in pi_by_id]
        # Filter out None values in case some IDs weren't found
        saved_pis_data = [pi for pi in saved_pis_data if pi is not None]
    
    return render_template(
        "draft_email.html",
        error=error,
        draft=draft,
        pi=pi,
        saved_pis=saved_pis_data,
        student_name=request.form.get("student_name", ""),
        student_email=request.form.get("student_email", ""),
        student_background=request.form.get("student_background", ""),
        research_interest=request.form.get("research_interest", "")
    )


@app.route("/try-demo")
def try_demo():
    """Demo mode - show sample matches without resume upload."""
    user_id = session.get("user_id")
    if not user_id:
        # Allow demo for non-logged-in users
        session["demo_mode"] = True
        return redirect(url_for("matches", demo="true"))
    return redirect(url_for("matches", demo="true"))

@app.route("/compare-labs")
def compare_labs():
    """Compare selected labs side-by-side."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    pi_ids = request.args.getlist("pi_ids")
    if not pi_ids:
        flash("Please select labs to compare.", "info")
        return redirect(url_for("saved_pis"))
    
    if len(pi_ids) < 2:
        flash("Please select at least 2 labs to compare.", "info")
        return redirect(url_for("saved_pis"))
    
    all_faculty = load_faculty()
    pi_by_id = {pi["id"]: pi for pi in all_faculty}
    labs_to_compare = [pi_by_id.get(pi_id) for pi_id in pi_ids if pi_id in pi_by_id]
    
    # Filter out None values in case some IDs weren't found
    labs_to_compare = [lab for lab in labs_to_compare if lab is not None]
    
    if len(labs_to_compare) < 2:
        flash("Could not find the selected labs. Please try again.", "error")
        return redirect(url_for("saved_pis"))
    
    return render_template("compare_labs.html", labs=labs_to_compare)

@app.route("/multi-email", methods=["GET", "POST"])
def multi_email():
    """Multi-lab outreach planner."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        selected_pi_ids = request.form.getlist("pi_ids")
        if not selected_pi_ids:
            flash("Please select at least one lab.", "error")
            return redirect(url_for("multi_email"))
        
        # This is similar to bulk_email but with enhanced UI
        return redirect(url_for("bulk_email") + "?selected=" + ",".join(selected_pi_ids))
    
    # Get saved PIs
    all_faculty = load_faculty()
    pi_by_id = {pi["id"]: pi for pi in all_faculty}
    saved_rows = SavedPI.query.filter_by(user_id=user_id).all()
    saved_pis_data = [pi_by_id.get(row.pi_id) for row in saved_rows if row.pi_id in pi_by_id]
    
    return render_template("multi_email.html", saved_pis=saved_pis_data)

@app.route("/feedback", methods=["POST"])
def submit_feedback():
    """Submit user feedback."""
    user_id = session.get("user_id")
    feedback_text = request.form.get("feedback", "").strip()
    page_context = request.form.get("page", "")
    
    if feedback_text:
        # In a real app, you'd save this to a database
        # For now, just log it or store in a simple file
        with open("feedback_log.txt", "a") as f:
            f.write(f"[{datetime.now()}] User: {user_id}, Page: {page_context}\n{feedback_text}\n\n")
        flash("Thank you for your feedback!", "success")
    
    return redirect(request.referrer or url_for("index"))

@app.route("/export-report")
def export_report():
    """Export user's top matches as PDF report."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    # Get user's saved PIs or top matches
    saved_rows = SavedPI.query.filter_by(user_id=user_id).all()
    all_faculty = load_faculty()
    pi_by_id = {pi["id"]: pi for pi in all_faculty}
    saved_pis_data = [pi_by_id.get(row.pi_id) for row in saved_rows if row.pi_id in pi_by_id][:10]
    
    user = User.query.get(user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("account"))
    
    # For now, return a simple text version
    # In production, use a library like reportlab or weasyprint for PDF
    return render_template("export_report.html", labs=saved_pis_data, user=user, current_date=datetime.now().strftime("%B %d, %Y"))

@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/onboarding", methods=["GET", "POST"])
def onboarding():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.session.add(profile)
        db.session.commit()
    
    step = int(request.args.get("step", 1))
    
    if request.method == "POST":
        if step == 1:
            major_field = request.form.get("major_field", "").strip()
            # Clear field if it's empty or just "none"
            if not major_field or major_field.lower() == 'none':
                major_field = None
            profile.major_field = major_field
            
            year_in_school = request.form.get("year_in_school", "").strip()
            profile.year_in_school = year_in_school if year_in_school else None
            profile.profile_completeness = 33
            db.session.commit()
            return redirect(url_for("onboarding", step=2))
        
        elif step == 2:
            # Handle multiple selections for looking_for
            looking_for_list = request.form.getlist("looking_for")
            if not looking_for_list:
                flash("Please select at least one option.", "error")
                return redirect(url_for("onboarding", step=2))
            looking_for = ",".join(looking_for_list)
            profile.looking_for = looking_for
            profile.profile_completeness = 66
            db.session.commit()
            return redirect(url_for("onboarding", step=3))
        
        elif step == 3:
            top_techniques = request.form.getlist("top_techniques")
            profile.top_techniques = ",".join(top_techniques)
            profile.onboarding_complete = True
            profile.profile_completeness = 100
            db.session.commit()
            flash("Profile setup complete! Start exploring labs.", "success")
            return redirect(url_for("account"))
    
    # Load all techniques for step 3
    all_faculty = load_faculty()
    all_techniques = set()
    for pi in all_faculty:
        if pi.get("lab_techniques"):
            techniques = [t.strip() for t in pi["lab_techniques"].split(",")]
            all_techniques.update(techniques)
    techniques_list = sorted(all_techniques)
    
    return render_template("onboarding.html", step=step, profile=profile, techniques=techniques_list)

@app.route("/account")
def account():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    user = User.query.get(user_id)
    if not user:
        flash("User not found. Please log in again.", "error")
        session.pop("user_id", None)
        return redirect(url_for("login"))
    
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    # Ensure profile_completeness has a default value if profile exists
    if profile and profile.profile_completeness is None:
        profile.profile_completeness = 0
        db.session.commit()
    
    return render_template("account.html", user=user, profile=profile)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login. Users can log in with either their email or username."""
    if request.method == "POST":
        # The form field is named "email" but can contain either email or username
        login_input = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not login_input:
            error = "Please provide either email or username."
            return render_template("login.html", error=error)
        
        if not password:
            error = "Password is required."
            return render_template("login.html", error=error)
        
        # Try to find user by email first (lowercase comparison)
        user = User.query.filter_by(email=login_input.lower()).first()
        
        # If not found by email, try to find by username (case-sensitive)
        if user is None:
            user = User.query.filter_by(username=login_input).first()

        # Check if the user exists and the password is correct
        if user is None or not user.check_password(password):
            error = "Invalid credentials."
            return render_template("login.html", error=error)

        # Login successful! Store the user info in the session so they stay logged in
        session["user_id"] = user.id
        session["username"] = user.username

        return redirect(url_for("account"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Handle new user registration. Validates input and creates the account."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validate that all required fields are filled in
        if not username or not email or not password or not confirm_password:
            error = "All fields are required."
            return render_template("signup.html", error=error)
        
        # Make sure username is long enough
        if len(username) < 3:
            error = "Username must be at least 3 characters long."
            return render_template("signup.html", error=error)

        # Check that both password fields match
        if password != confirm_password:
            error = "Passwords do not match."
            return render_template("signup.html", error=error)
        
        # Enforce minimum password length
        if len(password) < 6:
            error = "Password must be at least 6 characters long."
            return render_template("signup.html", error=error)

        # Make sure the username isn't already taken
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            error = "Username already taken. Please choose another."
            return render_template("signup.html", error=error)

        # Make sure the email isn't already registered
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            error = "An account with that email already exists."
            return render_template("signup.html", error=error)

        # Everything looks good! Create the new user account
        user = User(username=username, email=email)
        user.set_password(password)  # Hash the password before storing
        db.session.add(user)
        db.session.commit()

        # Automatically log them in after signup
        session["user_id"] = user.id
        session["username"] = user.username

        flash("Account created successfully!", "success")
        # Send new users to onboarding to set up their profile
        return redirect(url_for("onboarding"))

    # GET request
    return render_template("signup.html")

# Password Reset Routes - allow users to reset forgotten passwords

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """
    Handle password reset requests. Users enter their email and receive a reset link.
    """
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        
        if not email:
            error = "Please enter your email address."
            return render_template("forgot_password.html", error=error)
        
        # Find the user by email
        user = User.query.filter_by(email=email).first()
        
        # Always show success message (even if user doesn't exist) for security
        # This prevents attackers from knowing which emails are registered
        if user:
            # Generate a secure random token for password reset
            token = secrets.token_urlsafe(32)
            
            # Create expiration time (1 hour from now)
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            # Invalidate any existing reset tokens for this user
            existing_tokens = PasswordResetToken.query.filter_by(user_id=user.id, used=False).all()
            for existing_token in existing_tokens:
                existing_token.used = True
            
            # Create new reset token
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=expires_at
            )
            db.session.add(reset_token)
            db.session.commit()
            
            # Send password reset email
            # Get the base URL for the reset link
            base_url = request.url_root
            send_password_reset_email(user.email, token, base_url)
        
        # Show success message regardless of whether user exists (security best practice)
        flash("If an account with that email exists, we've sent a password reset link. Please check your email.", "info")
        return redirect(url_for("login"))
    
    # GET request - show the forgot password form
    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """
    Handle password reset with the token from the email link.
    Users can set a new password here.
    """
    # Find the reset token
    reset_token_obj = PasswordResetToken.query.filter_by(token=token).first()
    
    # Check if token exists and is valid
    if not reset_token_obj or not reset_token_obj.is_valid():
        flash("Invalid or expired password reset link. Please request a new one.", "error")
        return redirect(url_for("forgot_password"))
    
    # Get the user associated with this token
    user = User.query.get(reset_token_obj.user_id)
    if not user:
        flash("User not found. Please request a new password reset.", "error")
        return redirect(url_for("forgot_password"))
    
    if request.method == "POST":
        # Get the new password from the form
        new_password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        # Validate the passwords
        if not new_password or not confirm_password:
            error = "Please fill in all fields."
            return render_template("reset_password.html", token=token, error=error)
        
        if new_password != confirm_password:
            error = "Passwords do not match."
            return render_template("reset_password.html", token=token, error=error)
        
        if len(new_password) < 6:
            error = "Password must be at least 6 characters long."
            return render_template("reset_password.html", token=token, error=error)
        
        # Update the user's password
        user.set_password(new_password)
        
        # Mark the token as used so it can't be used again
        reset_token_obj.used = True
        
        # Save changes to database
        db.session.commit()
        
        # Success! Redirect to login
        flash("Your password has been reset successfully. Please log in with your new password.", "success")
        return redirect(url_for("login"))
    
    # GET request - show the reset password form
    return render_template("reset_password.html", token=token)


# This is the main entry point - it runs when you execute the file directly
if __name__ == "__main__":
    # Make sure all database tables exist before starting the server
    with app.app_context():
        db.create_all()
    # Start the Flask development server
    # We run on all interfaces (0.0.0.0) so it's accessible from other devices on the network
    # Using port 5001 instead of 5000 to avoid conflict with macOS AirPlay service
    # You can access it at http://localhost:5001 or http://127.0.0.1:5001
    app.run(debug=True, host='0.0.0.0', port=5001)
