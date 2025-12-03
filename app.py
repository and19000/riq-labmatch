import os
import json
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GPT_MODEL = "gpt-4.1-mini"  # cheapest model

app = Flask(__name__)

app.config["SECRET_KEY"] = "dev-secret-change-later"  # needed for sessions

# SQLite database file in the project root
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///riq.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

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

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


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
    # Read filters from query string (?school=...&department=...)
    selected_school = request.args.get("school", "").strip()
    selected_department = request.args.get("department", "").strip()

    all_faculty = load_faculty()

    filtered = []
    for pi in all_faculty:
        if selected_school and pi["school"] != selected_school:
            continue
        if selected_department and pi["department"] != selected_department:
            continue
        filtered.append(pi)

    # For now, no real fit score – that will come from AI later
    # We just pass the filtered list to the template.
    return render_template(
        "general.html",
        faculty_list=filtered,
        selected_school=selected_school,
        selected_department=selected_department,
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
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            # Pass the filename to the template so we can confirm to the user
            return render_template(
                "resume_upload.html",
                uploaded_filename=filename,
                error=None,
            )
        else:
            error = "File type not allowed. Please upload a PDF or DOCX."
            return render_template("resume_upload.html", error=error)

    # GET request → just show the empty form
    return render_template("resume_upload.html")


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


@app.route("/draft-email")
def draft_email():
    # Later we'll add a version that takes a PI id.
    return render_template("draft_email.html")


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/account")
def account():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))


@app.route("/login")
    user = User.query.get(user_id)
    if user is None:
        # Session had a bad user_id; clear it and force login
        session.pop("user_id", None)
        return redirect(url_for("login"))

    return render_template("account.html", user=user)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            error = "Both email and password are required."
            return render_template("login.html", error=error)

        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            error = "Invalid email or password."
            return render_template("login.html", error=error)

        # Credentials are valid → store user in session
        session["user_id"] = user.id

        return redirect(url_for("account"))

    return render_template("login.html")


@app.route("/signup")
@app.route("/logout")
def logout():
    session.pop("user_id", None)
    return redirect(url_for("index"))

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Basic validation
        if not email or not password or not confirm_password:
            error = "All fields are required."
            return render_template("signup.html", error=error)

        if password != confirm_password:
            error = "Passwords do not match."
            return render_template("signup.html", error=error)

        # Check if email already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            error = "An account with that email already exists."
            return render_template("signup.html", error=error)

        # Create the user
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Log the user in (store in session)
        session["user_id"] = user.id

        # Redirect to account page
        return redirect(url_for("account"))

    # GET request
    return render_template("signup.html")


if __name__ == "__main__":
    app.run(debug=True)
