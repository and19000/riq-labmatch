import os

from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GPT_MODEL = "gpt-4.1-mini"  # cheapest model

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


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
    return render_template("account.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/signup")
def signup():
    return render_template("signup.html")


if __name__ == "__main__":
    app.run(debug=True)
