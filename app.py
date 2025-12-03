from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/general")
def general():
    return render_template("general.html")

@app.route("/resume")
def resume_upload():
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