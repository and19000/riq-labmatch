import os
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

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

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename: str) -> bool:
    """Return True if the file has an allowed extension."""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/general")
def general():
    return render_template("general.html")

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
    return render_template("saved_pis.html")

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