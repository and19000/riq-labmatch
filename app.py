import os
import json
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GPT_MODEL = "gpt-4o-mini"  # cost-effective model

app = Flask(__name__)

app.config["SECRET_KEY"] = "dev-secret-change-later"  # needed for sessions

# SQLite database file in the project root
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///riq.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        # Use pbkdf2:sha256 for Python 3.9 compatibility (scrypt requires Python 3.10+)
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

class SavedPI(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pi_id = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "pi_id", name="uq_user_pi"),
    )

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    resume_text = db.Column(db.Text)  # Extracted text from resume for AI matching

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    major_field = db.Column(db.String(255))
    looking_for = db.Column(db.String(255))  # thesis lab, summer RA, rotation, gap year
    top_techniques = db.Column(db.Text)  # JSON array or comma-separated
    onboarding_complete = db.Column(db.Boolean, default=False)
    profile_completeness = db.Column(db.Integer, default=0)  # 0-100
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize database
def init_db():
    """Initialize database and run migrations."""
    with app.app_context():
        db.create_all()
        
        # Migration: Add username column to User table if it doesn't exist
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            
            # Check if user table exists
            if 'user' in inspector.get_table_names():
                columns = [col['name'] for col in inspector.get_columns('user')]
                
                if 'username' not in columns:
                    # Add username column using raw SQL
                    # SQLite supports ADD COLUMN in ALTER TABLE
                    with db.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE user ADD COLUMN username VARCHAR(80)"))
                    print("Migration: Added username column to user table")
        except Exception as e:
            # If table doesn't exist yet, create_all will handle it
            # Or if migration fails, continue anyway
            print(f"Migration check: {e}")

init_db()


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
FACULTY_PATH = os.path.join(DATA_DIR, "faculty.json")


def load_faculty():
    """Load all faculty from the JSON file."""
    with open(FACULTY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_faculty_by_id(pi_id: str):
    """Return a single PI dict by id, or None."""
    all_faculty = load_faculty()
    for pi in all_faculty:
        if pi["id"] == pi_id:
            return pi
    return None

def allowed_file(filename: str) -> bool:
    """Return True if the file has an allowed extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def process_faculty_batch(faculty_batch, resume_info, batch_num, total_batches):
    """Process a batch of faculty members and return match scores."""
    try:
        # Create concise summaries for this batch (optimized for speed)
        faculty_summaries = []
        for pi in faculty_batch:
            # More concise format to reduce token count and processing time
            summary = f"{pi['name']} ({pi['id']}): {pi['research_areas']}"
            if pi.get('lab_techniques'):
                summary += f" | Techniques: {pi['lab_techniques'][:100]}"  # Truncate long technique lists
            summary += f" | {pi['department']}, {pi['school']}"
            faculty_summaries.append(summary)
        
        faculty_text = "\n".join(faculty_summaries)
        
        # Optimized, more concise prompt for faster processing
        prompt = f"""Match student resume with compatible labs. Return JSON array only.

STUDENT: {resume_info[:500]}

LABS (Batch {batch_num + 1}/{total_batches}):
{faculty_text}

Scoring (40% research match, 25% skills, 15% level, 10% dept, 10% impact):
- 90-100: Exceptional | 80-89: Excellent | 70-79: Good | 60-69: Moderate | 50-59: Weak | <50: Exclude

Return JSON array: [{{"pi_id": "id", "score": 85, "reason": "brief reason"}}]
Only include labs with score >= 50. Rank highest to lowest."""

        # Make API call - OpenAI client handles timeouts internally
        # Using concise prompt and lower temperature for faster responses
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
        
        # Try to extract JSON array from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if json_match:
            try:
                matches_data = json.loads(json_match.group())
                return matches_data
            except json.JSONDecodeError:
                # Try to find matches key if it's a JSON object
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
        # Return empty list on error - will be handled by caller
        print(f"Error processing batch {batch_num + 1}: {str(e)}")
        return []


@app.route("/test-gpt")
def test_gpt():
    """Simple route to verify OpenAI + .env are working."""
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
    return render_template("index.html")


@app.route("/general")
def general():
    # Read filters from query string
    selected_school = request.args.get("school", "").strip()
    selected_department = request.args.get("department", "").strip()
    selected_technique = request.args.get("technique", "").strip()
    selected_location = request.args.get("location", "").strip()

    all_faculty = load_faculty()

    # Get unique values for filter dropdowns
    schools = sorted(set(pi["school"] for pi in all_faculty))
    departments = sorted(set(pi["department"] for pi in all_faculty))
    
    # Extract unique lab techniques and locations
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

    filtered = []
    for pi in all_faculty:
        if selected_school and pi["school"] != selected_school:
            continue
        if selected_department and pi["department"] != selected_department:
            continue
        if selected_technique:
            pi_techniques = [t.strip().lower() for t in (pi.get("lab_techniques", "") or "").split(",")]
            if selected_technique.lower() not in pi_techniques:
                continue
        if selected_location:
            pi_location = pi.get("specific_location", pi["location"])
            if selected_location not in pi_location:
                continue
        filtered.append(pi)

    # Check which PIs are already saved by the user
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
    """Show AI-ranked lab matches based on user's resume."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    # Check for demo mode
    use_demo = request.args.get("demo") == "true"
    
    # Get user's most recent resume
    resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    
    if not resume and not use_demo:
        flash("Please upload a resume first to see your matches.", "info")
        return redirect(url_for("resume_upload"))
    
    all_faculty = load_faculty()
    
    # Prepare resume info
    if use_demo:
        resume_info = """Computer Science major with strong background in machine learning and neuroscience. 
        Research experience: 2 years in computational neuroscience lab working with neural networks and electrophysiology data.
        Skills: Python, PyTorch, MATLAB, data analysis, statistical modeling.
        Interests: Computational neuroscience, brain-computer interfaces, AI applications in healthcare.
        Publications: 1 first-author paper in preparation on neural decoding algorithms."""
    else:
        resume_info = resume.resume_text if resume.resume_text else 'Resume uploaded but text extraction pending. Analyze based on filename and typical student profile.'
    
    # Use parallel batch processing to speed up matching
    try:
        # Split faculty into batches for parallel processing
        # Smaller batches = more parallelism, faster overall
        BATCH_SIZE = 10  # Reduced from 15 for more parallel requests
        faculty_to_process = all_faculty[:100]  # Process top 100 labs (reduced from 150 for speed)
        batches = [faculty_to_process[i:i + BATCH_SIZE] for i in range(0, len(faculty_to_process), BATCH_SIZE)]
        total_batches = len(batches)
        
        # Process batches in parallel using ThreadPoolExecutor
        # Increased workers for more parallelism (20 instead of 10)
        all_matches_data = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Submit all batch processing tasks
            future_to_batch = {
                executor.submit(process_faculty_batch, batch, resume_info, idx, total_batches): idx 
                for idx, batch in enumerate(batches)
            }
            
            # Collect results as they complete
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
        # Fallback: return all labs without ranking if AI fails
        matches_data = [{"pi_id": pi["id"], "score": 50, "reason": "Unable to generate match score"} for pi in all_faculty]
        flash(f"AI matching temporarily unavailable. Showing all labs. Error: {str(e)}", "warning")
    
    # Create a dict of pi_id -> match data
    pi_by_id = {pi["id"]: pi for pi in all_faculty}
    ranked_matches = []
    
    for match in matches_data:
        pi_id = match.get("pi_id")
        if pi_id in pi_by_id:
            pi = pi_by_id[pi_id].copy()
            pi["match_score"] = match.get("score", 50)
            pi["match_reason"] = match.get("reason", "Match found")
            ranked_matches.append(pi)
    
    # Sort by score descending
    ranked_matches.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    
    # Check which PIs are already saved
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
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    # Avoid duplicates thanks to UniqueConstraint, but also check manually
    existing = SavedPI.query.filter_by(user_id=user_id, pi_id=pi_id).first()
    if existing is None:
        saved = SavedPI(user_id=user_id, pi_id=pi_id)
        db.session.add(saved)
        db.session.commit()

    # Redirect back to the page we came from if possible
    return redirect(request.referrer or url_for("saved_pis"))


@app.route("/resume", methods=["GET", "POST"])
def resume_upload():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    if request.method == "POST":
        # Check that the form actually included a file
        if "resume" not in request.files:
            error = "No file part in the form."
            return render_template("resume_upload.html", error=error)

        file = request.files["resume"]

        # If user submitted without choosing a file
        if file.filename == "":
            error = "No file selected."
            return render_template("resume_upload.html", error=error)

        # Validate the extension and save the file
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Add user_id to filename to avoid conflicts
            user_filename = f"{user_id}_{filename}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], user_filename)
            file.save(save_path)
            
            # Try to extract text from resume (basic implementation)
            # For PDF/DOCX, you'd need libraries like PyPDF2 or python-docx
            resume_text = ""  # Placeholder - would extract actual text here
            
            # Save resume record to database
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

    # GET request → show form and any existing resume
    existing_resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    return render_template("resume_upload.html", existing_resume=existing_resume)


@app.route("/saved")
def saved_pis():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    all_faculty = load_faculty()
    pi_by_id = {pi["id"]: pi for pi in all_faculty}

    saved_rows = SavedPI.query.filter_by(user_id=user_id).all()
    saved_pis_data = []
    for row in saved_rows:
        pi = pi_by_id.get(row.pi_id)
        if pi:
            saved_pis_data.append(pi)

    return render_template("saved_pis.html", saved_pis=saved_pis_data)


@app.route("/unsave-pi/<pi_id>", methods=["POST"])
def unsave_pi(pi_id):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

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
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    error = None
    draft = None
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
                    # Get user's resume for context
                    user_resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
                    resume_context = ""
                    if user_resume and user_resume.resume_text:
                        resume_context = f"\nStudent's Resume Summary: {user_resume.resume_text[:500]}"
                    
                    # Enhanced email generation with better context
                    prompt = f"""Write a professional, personalized cold email to {pi['name']}, {pi['title']} at {pi['department']}, {pi['school']}.

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

EMAIL REQUIREMENTS:
1. Subject line: Clear, specific, and professional (e.g., "Research Opportunity Inquiry - [Your Name]")
2. Opening: Brief introduction with your name, academic level, and institution
3. Body paragraph 1: Express specific interest in their research - mention 1-2 specific research areas or papers
4. Body paragraph 2: Highlight relevant background/skills that align with their lab
5. Body paragraph 3: Explain what you hope to contribute and learn
6. Closing: Polite request for a meeting or conversation opportunity
7. Keep total length under 250 words
8. Be genuine, enthusiastic, but not overly casual
9. Show you've researched their work specifically

Format the response as:
Subject: [subject line]

Dear Dr. [Last Name],

[email body]

Best regards,
{student_name}"""

                    completion = client.chat.completions.create(
                        model=GPT_MODEL,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that writes professional academic emails."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                    )
                    draft = completion.choices[0].message.content
                except Exception as e:
                    error = f"Error generating email draft: {str(e)}"
    
    # Get all faculty for dropdown if no PI selected
    all_faculty = load_faculty() if not pi else None
    
    return render_template(
        "draft_email.html",
        error=error,
        draft=draft,
        pi=pi,
        all_faculty=all_faculty,
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
            profile.major_field = major_field
            profile.profile_completeness = 33
            db.session.commit()
            return redirect(url_for("onboarding", step=2))
        
        elif step == 2:
            looking_for = request.form.get("looking_for", "").strip()
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
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not password:
            error = "Password is required."
            return render_template("login.html", error=error)
        
        # Allow login with either email or username
        if email:
            user = User.query.filter_by(email=email).first()
        elif username:
            user = User.query.filter_by(username=username).first()
        else:
            error = "Please provide either email or username."
            return render_template("login.html", error=error)

        if user is None or not user.check_password(password):
            error = "Invalid credentials."
            return render_template("login.html", error=error)

        # Credentials are valid → store user in session
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
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Basic validation
        if not username or not email or not password or not confirm_password:
            error = "All fields are required."
            return render_template("signup.html", error=error)
        
        if len(username) < 3:
            error = "Username must be at least 3 characters long."
            return render_template("signup.html", error=error)

        if password != confirm_password:
            error = "Passwords do not match."
            return render_template("signup.html", error=error)
        
        if len(password) < 6:
            error = "Password must be at least 6 characters long."
            return render_template("signup.html", error=error)

        # Check if username already exists
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            error = "Username already taken. Please choose another."
            return render_template("signup.html", error=error)

        # Check if email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            error = "An account with that email already exists."
            return render_template("signup.html", error=error)

        # Create the user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Log the user in (store in session)
        session["user_id"] = user.id
        session["username"] = user.username

        flash("Account created successfully!", "success")
        # Redirect to onboarding for new users
        return redirect(url_for("onboarding"))

    # GET request
    return render_template("signup.html")


if __name__ == "__main__":
    # Ensure database is initialized
    with app.app_context():
        db.create_all()
    # Run on all interfaces (0.0.0.0) to make it accessible
    # Using port 5001 to avoid conflict with macOS AirPlay on port 5000
    # Access via http://localhost:5001 or http://127.0.0.1:5001
    app.run(debug=True, host='0.0.0.0', port=5001)
