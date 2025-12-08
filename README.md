# RIQ Lab Matcher - User Manual

## Overview

RIQ Lab Matcher is a comprehensive Flask-based web application designed to help students discover and connect with research opportunities at leading universities, particularly MIT and Harvard. The application serves as a bridge between students seeking research positions and Principal Investigators (PIs) who lead research laboratories. The platform combines a curated database of faculty members with AI-powered matching capabilities to help students find labs that align with their skills, interests, and career goals.

The application provides several key features to streamline the research lab discovery process. Students can browse an extensive database of faculty members organized by university and department, save their favorite PIs for later reference, upload their resumes for AI-powered matching, and generate personalized email drafts to contact potential research mentors. The system uses OpenAI's GPT-4o-mini model to analyze student profiles and resumes, matching them with compatible research labs based on research interests, techniques, and academic background.

This user manual will guide you through every step of setting up, configuring, and using the RIQ Lab Matcher application. Whether you are a staff member evaluating the project, a developer looking to extend its functionality, or an end user wanting to explore research opportunities, this documentation will provide all the information you need to get started and use the application effectively.

## Prerequisites

Before you begin setting up the RIQ Lab Matcher application, ensure that you have the following prerequisites installed on your system:

- **Python 3.9 or higher**: The application is built using Python and requires version 3.9 or later. You can check your Python version by running `python3 --version` in your terminal. If you don't have Python installed, download it from [python.org](https://www.python.org/downloads/).

- **pip (Python Package Manager)**: pip is typically included with Python installations. Verify it's installed by running `pip3 --version`. If it's not available, you may need to install it separately or reinstall Python.

- **Git (optional)**: If you're cloning the repository from a version control system, you'll need Git installed. However, if you've received the project as a ZIP file or folder, Git is not required.

- **A modern web browser**: The application is accessed through a web browser. We recommend using Chrome, Firefox, Safari, or Edge for the best experience.

- **An OpenAI API Key (required for AI features)**: The application uses OpenAI's API for AI-powered matching and email generation. You'll need to obtain an API key from [OpenAI's website](https://platform.openai.com/api-keys). The free tier may have usage limits, but it's sufficient for testing and development purposes.

## Installation and Setup

### Step 1: Navigate to the Project Directory

First, open your terminal (Command Prompt on Windows, Terminal on macOS/Linux) and navigate to the project directory. If you received the project as a folder, locate it on your system. For example:

```bash
cd /path/to/riq-labmatch
```

If you're on Windows, the path might look like `C:\Users\YourName\riq-labmatch`. On macOS or Linux, it might be something like `/Users/YourName/riq-labmatch` or `/home/YourName/riq-labmatch`.

### Step 2: Create a Virtual Environment

A virtual environment isolates the project's dependencies from other Python projects on your system, preventing conflicts. Create a virtual environment by running:

```bash
python3 -m venv venv
```

On Windows, you might need to use `python` instead of `python3`. If you encounter any errors, try `py -m venv venv` on Windows.

### Step 3: Activate the Virtual Environment

After creating the virtual environment, you need to activate it before installing dependencies or running the application. The activation command differs by operating system:

**On macOS and Linux:**
```bash
source venv/bin/activate
```

**On Windows (Command Prompt):**
```bash
venv\Scripts\activate
```

**On Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

When the virtual environment is activated, you should see `(venv)` at the beginning of your terminal prompt. This indicates that you're working within the virtual environment. If you don't see this, the activation may have failed—check that you're in the correct directory and that the `venv` folder was created successfully.

### Step 4: Install Dependencies

With the virtual environment activated, install all required Python packages using pip:

```bash
pip install -r requirements.txt
```

This command reads the `requirements.txt` file, which lists all necessary dependencies including Flask (the web framework), OpenAI (for AI features), SQLAlchemy (for database operations), and other supporting libraries. The installation may take a minute or two depending on your internet connection. You should see progress messages as each package is downloaded and installed.

If you encounter any errors during installation, they're usually related to missing system dependencies or network issues. On Linux, you might need to install Python development headers (`sudo apt-get install python3-dev` on Ubuntu/Debian). On macOS, you might need Xcode Command Line Tools (`xcode-select --install`).

### Step 5: Configure Environment Variables

The application requires an OpenAI API key to function properly. This key is stored in a `.env` file in the project root directory to keep it secure and separate from the codebase. Create a new file named `.env` (note the leading dot) in the project root directory.

**On macOS/Linux:**
```bash
touch .env
```

**On Windows:**
You can create the file using a text editor or by running:
```bash
type nul > .env
```

Open the `.env` file in a text editor and add the following line, replacing `your_openai_api_key_here` with your actual OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Important Security Notes:**
- Never share your API key or commit the `.env` file to version control. The `.env` file is already included in `.gitignore` to prevent accidental commits.
- If you don't have an OpenAI API key, you can obtain one by creating an account at [platform.openai.com](https://platform.openai.com) and navigating to the API keys section.
- The application will still run without an API key, but AI-powered features (matching and email drafting) will not work.

### Step 6: Initialize the Database

The application uses SQLite, a lightweight database that stores data in a local file. The database will be automatically created when you first run the application, so you don't need to do anything manually. However, if you want to explicitly create the database tables before running the app, you can run:

```bash
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

This command imports the Flask app and database objects, creates an application context (required for database operations), and creates all necessary tables. The database file will be created in the `instance/` directory as `riq.db`. If the `instance/` directory doesn't exist, it will be created automatically.

### Step 7: Verify Data Files

The application requires a `faculty.json` file in the `data/` directory containing information about Principal Investigators. Verify that this file exists:

```bash
ls data/faculty.json
```

On Windows, use `dir data\faculty.json`. If the file is missing, the application may not function correctly when browsing faculty members. The file should be quite large (typically several megabytes) as it contains detailed information about many faculty members.

## Running the Application

### Starting the Server

Once you've completed the setup steps above, you're ready to run the application. Make sure your virtual environment is activated (you should see `(venv)` in your terminal prompt), then start the Flask development server:

```bash
python app.py
```

On some systems, you might need to use `python3` instead of `python`. The server will start and you should see output similar to:

```
 * Running on http://0.0.0.0:5001
 * Running on http://127.0.0.1:5001
```

**Important Note About Port 5001:** The application runs on port 5001 instead of the default Flask port 5000. This is intentional to avoid conflicts with macOS's AirPlay service, which uses port 5000. If port 5001 is already in use on your system, you can modify the port number in `app.py` (look for `port=5001` near the end of the file).

### Accessing the Application

Once the server is running, open your web browser and navigate to one of the following URLs:

- `http://localhost:5001`
- `http://127.0.0.1:5001`

You should see the RIQ Lab Matcher homepage. The server will continue running until you stop it by pressing `Ctrl+C` in the terminal where it's running.

### Running in Background (Optional)

If you want the server to continue running after closing your terminal window, you can use the provided startup script (on macOS/Linux):

```bash
./START_SERVER.sh --background
```

This will start the server in the background and save logs to `server.log`. To stop a background server, run:

```bash
pkill -f 'python app.py'
```

On Windows, you can achieve similar functionality by running the server in a separate Command Prompt window or using task scheduling tools.

## Using the Application

### Creating an Account

When you first access the application, you'll need to create an account to use most features. Click on "Sign Up" or navigate to `/signup` to create a new account. You'll be asked to provide:

- **Username**: A unique username for your account
- **Email**: Your email address (must be unique and valid)
- **Password**: A password of at least 6 characters

After submitting the signup form, you'll be automatically logged in and can start using the application.

### Logging In

If you already have an account, click "Login" or navigate to `/login` to access your account. Enter your email and password to log in. If you've forgotten your password, you can use the "Forgot Password" link to reset it via email (if email functionality is configured).

### Browsing Faculty Members

The core feature of the application is browsing the database of Principal Investigators. Navigate to the "Browse Labs" page (accessible from the homepage or at `/general`) to see all available faculty members. You can filter the results by:

- **University/School**: Filter by institution (e.g., MIT, Harvard)
- **Department**: Filter by academic department (e.g., Biology, Computer Science, Chemistry)

Use the dropdown menus at the top of the page to apply filters. The results will update automatically to show only faculty members matching your selected criteria. Each faculty member card displays their name, affiliation, research interests, and other relevant information.

### Saving Favorite PIs

As you browse through faculty members, you can save PIs that interest you to your account for easy access later. Click the "Save" button on any faculty member card to add them to your saved list. You can view all your saved PIs by navigating to the "Saved PIs" page (accessible from your account menu or at `/saved`). From there, you can remove PIs from your saved list if you change your mind.

### Uploading Your Resume

To take advantage of the AI-powered matching features, you should upload your resume. Navigate to the "Upload Resume" page (accessible from the account menu or at `/resume`) and select a PDF or DOCX file from your computer. The application will:

1. Store your resume file securely
2. Extract text from the resume for analysis
3. Use this information for AI-powered lab matching

You can upload multiple resumes, but only the most recent one will be used for matching purposes. The application validates file types and sizes to ensure security and performance.

### AI-Powered Lab Matching

Once you've uploaded a resume and completed your profile (including your major, year in school, and research interests), you can access the AI-powered matching feature. Navigate to the "Matches" page (at `/matches`) to see personalized lab recommendations. The system analyzes:

- Your resume content and experience
- Your stated research interests
- Your preferred techniques and methods
- Your academic background and year in school

Based on this analysis, the AI generates a ranked list of compatible research labs, explaining why each match is a good fit for your profile. This feature requires a valid OpenAI API key to function.

### Drafting Emails to PIs

One of the most valuable features is the ability to generate personalized email drafts for contacting Principal Investigators. Navigate to the "Draft Email" page (at `/draft-email`) and:

1. Select a PI from your saved list or search for one
2. Optionally customize the email tone and content
3. Click "Generate Email" to create a personalized draft

The AI will generate a professional, compelling email that:
- Introduces you and your background
- Explains why you're interested in their research
- Highlights relevant experience from your resume
- Requests a meeting or research opportunity

You can edit the generated email before copying it to your email client. The application also supports bulk email drafting for multiple PIs at once, accessible at `/bulk-email`.

### Comparing Labs

If you're deciding between multiple research opportunities, you can use the lab comparison feature (at `/compare-labs`). Select two or more PIs to compare side-by-side, viewing their research interests, techniques, publications, and other relevant information in a structured format to help you make an informed decision.

### Managing Your Account

Access your account settings by clicking on your username in the navigation bar or navigating to `/account`. Here you can:

- View your account information
- Update your profile (major, year in school, research interests)
- Manage your saved PIs
- View your uploaded resumes
- Change your password

## Project Structure

Understanding the project structure can help you navigate the codebase and troubleshoot issues:

```
riq-labmatch/
├── app.py                 # Main Flask application file containing all routes and logic
├── requirements.txt       # Python package dependencies
├── README.md             # This documentation file
├── .env                  # Environment variables (API keys) - not in version control
├── .gitignore           # Files and directories to exclude from version control
├── data/
│   └── faculty.json     # Database of Principal Investigators (large JSON file)
├── templates/           # HTML templates for web pages
│   ├── base.html        # Base template with navigation and common elements
│   ├── index.html       # Homepage
│   ├── login.html       # Login page
│   ├── signup.html      # Registration page
│   ├── account.html     # User account management
│   ├── general.html     # Faculty browsing page with filters
│   ├── saved_pis.html   # List of saved PIs
│   ├── resume_upload.html # Resume upload interface
│   ├── draft_email.html      # Email drafting interface
│   ├── bulk_email.html      # Bulk email drafting
│   ├── matches.html         # AI-powered lab matches
│   ├── compare_labs.html    # Lab comparison tool
│   ├── help.html            # Help and documentation page
│   ├── onboarding.html      # New user onboarding flow
│   ├── forgot_password.html # Password recovery
│   └── reset_password.html  # Password reset form
├── static/              # Static files (CSS, JavaScript, images)
│   ├── css/
│   │   └── style.css    # Main stylesheet
│   ├── app.js           # Client-side JavaScript
│   └── images/          # Image assets (logos, icons)
├── instance/            # Runtime files (created automatically)
│   └── riq.db          # SQLite database file
├── uploads/            # User-uploaded resumes (created automatically)
└── venv/               # Virtual environment (created during setup)
```

## Configuration Options

### Database Configuration

The application uses SQLite by default, which requires no additional configuration. The database file is stored at `instance/riq.db`. If you need to use a different database (such as PostgreSQL for production), you can modify the `SQLALCHEMY_DATABASE_URI` in `app.py`. However, this requires additional setup and is beyond the scope of this user manual.

### Port Configuration

The application runs on port 5001 by default. To change this, edit the last line of `app.py`:

```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

Change `port=5001` to your desired port number. Remember that ports below 1024 typically require administrator privileges on Unix-like systems.

### Secret Key

The application uses a secret key for encrypting session data. In the current version, this is set to a default development value (`"dev-secret-change-later"`). **For production use, you must change this to a long, random string.** You can generate a secure secret key using Python:

```python
import secrets
print(secrets.token_hex(32))
```

Then update the `SECRET_KEY` in `app.py` with the generated value.

### OpenAI Model Configuration

The application uses GPT-4o-mini by default. To change this, modify the `GPT_MODEL` variable near the top of `app.py`:

```python
GPT_MODEL = "gpt-4o-mini"
```

You can change this to other OpenAI models like `"gpt-4"` or `"gpt-3.5-turbo"`, but be aware that different models have different pricing and capability characteristics.

## Troubleshooting

### The Server Won't Start

**Problem:** When you run `python app.py`, you get an error or the server doesn't start.

**Solutions:**
1. **Check Python version**: Ensure you have Python 3.9 or higher. Run `python3 --version` to check.
2. **Verify virtual environment**: Make sure your virtual environment is activated (you should see `(venv)` in your prompt).
3. **Check dependencies**: Reinstall dependencies with `pip install -r requirements.txt --upgrade`.
4. **Port already in use**: If you see an error about port 5001 being in use, either stop the other application using that port or change the port in `app.py`.
5. **Check for syntax errors**: If there are Python syntax errors in `app.py`, the server won't start. Check the error message for the specific line number.

### "This site can't be reached" or Connection Errors

**Problem:** The browser shows a connection error when trying to access `http://localhost:5001`.

**Solutions:**
1. **Verify server is running**: Check your terminal to ensure the Flask server is actually running. You should see "Running on http://127.0.0.1:5001" in the output.
2. **Check the URL**: Make sure you're using `http://localhost:5001` or `http://127.0.0.1:5001` (not `https://`).
3. **Try a different browser**: Sometimes browser cache or extensions can cause issues. Try Chrome, Firefox, or Safari.
4. **Check firewall settings**: Your firewall might be blocking the connection. Temporarily disable it to test, or add an exception for Python.
5. **Verify port**: Check that nothing else is using port 5001 by running `lsof -i:5001` (macOS/Linux) or `netstat -ano | findstr :5001` (Windows).

### Database Errors

**Problem:** You see database-related errors when using the application.

**Solutions:**
1. **Recreate the database**: Delete the `instance/riq.db` file and let the application recreate it on startup.
2. **Check file permissions**: Ensure the application has write permissions in the `instance/` directory.
3. **Verify database file**: Check that `instance/riq.db` exists. If it doesn't, the application should create it automatically, but you can manually trigger creation using the command in Step 6 of the Installation section.

### AI Features Not Working

**Problem:** The matching or email drafting features don't work or show errors.

**Solutions:**
1. **Check API key**: Verify that your `.env` file exists and contains a valid `OPENAI_API_KEY`. The key should start with `sk-`.
2. **Test API connection**: Navigate to `/test-gpt` in your browser to test the OpenAI API connection.
3. **Check API credits**: Ensure your OpenAI account has available credits. You can check this at [platform.openai.com/usage](https://platform.openai.com/usage).
4. **Verify internet connection**: The application needs internet access to communicate with OpenAI's API.
5. **Check error messages**: Look at the browser console (F12) and server terminal output for specific error messages that might indicate the problem.

### File Upload Issues

**Problem:** You can't upload resumes or get errors when trying to upload.

**Solutions:**
1. **Check file format**: Only PDF and DOCX files are supported. Ensure your file has the correct extension.
2. **Check file size**: Very large files might cause issues. Try a smaller file to test.
3. **Verify uploads directory**: The `uploads/` directory should be created automatically, but ensure it exists and has write permissions.
4. **Check file permissions**: On some systems, you may need to manually create the `uploads/` directory with appropriate permissions.

### Login/Signup Issues

**Problem:** You can't create an account or log in.

**Solutions:**
1. **Check email uniqueness**: Each email can only be used for one account. If you're trying to sign up with an email that's already registered, use a different email or try logging in instead.
2. **Verify password requirements**: Passwords must be at least 6 characters long.
3. **Check database**: Ensure the database is properly initialized and accessible.
4. **Clear browser cache**: Sometimes cached data can cause authentication issues. Try clearing your browser cache or using an incognito/private window.

## Common Questions

**Q: Do I need an OpenAI API key to use the application?**  
A: The application will run without an API key, but AI-powered features (lab matching and email drafting) will not function. You can still browse faculty members, save PIs, and upload resumes without an API key.

**Q: Can I use this application in production?**  
A: The current version is configured for development use. For production deployment, you should: change the secret key, use a production-grade web server (like Gunicorn), configure a proper database (PostgreSQL recommended), set up proper error logging, and implement HTTPS. The current setup with SQLite and the Flask development server is suitable for testing and evaluation only.

**Q: How do I add more faculty members to the database?**  
A: Faculty data is stored in `data/faculty.json` as a JSON file. You can add entries to this file following the existing structure. However, modifying this file requires understanding the data schema and should be done carefully.

**Q: Can I change the port the application runs on?**  
A: Yes, edit the last line of `app.py` and change `port=5001` to your desired port number. Remember to update any bookmarks or scripts that reference the old port.

**Q: How do I reset my password if I forget it?**  
A: Use the "Forgot Password" link on the login page. This will send a password reset email to your registered email address (if email functionality is configured). If email is not configured, you may need to manually reset the password in the database or contact an administrator.

**Q: Is my data secure?**  
A: The application uses password hashing (never storing plain-text passwords) and secure session management. However, this is a development version. For production use, you should implement additional security measures including HTTPS, rate limiting, and regular security audits.

**Q: Can I export my saved PIs or matches?**  
A: Yes, the application includes an export feature at `/export-report` that allows you to download a report of your saved PIs and matches in various formats.

## Additional Resources

- **Help Page**: The application includes a built-in help page accessible at `/help` that provides quick reference information.
- **Flask Documentation**: For developers wanting to extend the application, the [Flask documentation](https://flask.palletsprojects.com/) provides comprehensive guides.
- **OpenAI API Documentation**: For understanding the AI features, refer to the [OpenAI API documentation](https://platform.openai.com/docs).

## Support and Contact

If you encounter issues not covered in this manual or need additional assistance, please refer to the error messages displayed by the application, check the server logs (if running in background mode, check `server.log`), and review the troubleshooting section above. For development-related questions, consult the code comments in `app.py`, which provide detailed explanations of the application's functionality.

---

**Last Updated**: This documentation reflects the current state of the RIQ Lab Matcher application. The application may be updated over time, and this manual should be reviewed periodically to ensure accuracy.
