# Research IQ (RIQ) Lab Matcher - User Manual

## Overview

RIQ Lab Matcher is a Flask-based web application that helps users discover and connect with research opportunities at Harvard and MIT. The website serves as a bridge between users seeking research positions and Principal Investigators (PIs) who lead research labs. RIQ provides key features to streamline the lab discovery process. Users are able to browse through an organized database of faculty members, save their favorites for later reference, upload their resumes for AI-powered (ChatGPT-4o-mini) matching, and create email drafts to contact PIs. 

## Necessary Materials/Installations

- **Python 3.9 or higher**

- **pip (to install packages)**
    -**flask**
    -**openai**
    -**python-dotenv**
    -**sqlalchemy**
    -**requests**
    -**urllib3**

- **Git (if cloning)**

- **A modern web browser (e.g. Safari or Chrome)**

- **An OpenAI API Key (for AI features)**

## Installation and Setup

### Step 1: Navigate to the Project Directory

First, open your terminal (command prompt on Windows, terminal on macOS/Linux) and navigate to the project directory. If you received the project as a folder, locate it on your system. For example:

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

After creating the virtual environment, you need to activate it before installing dependencies or running the application. 

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

If the virtual environment is activated, you should see `(venv)` at the beginning of your terminal prompt. This indicates that you're working within the virtual environment. 

### Step 4: Install Dependencies

With the virtual environment activated, install the required Python packages (see Necessary Materials/Installations) using pip:

```bash
pip install -r requirements.txt
```

### Step 5: Configure Environment Variables

The application requires an OpenAI API key to function fully. The application will still run without an API key, but AI-powered features (matching and email drafting) won't work. This key is stored in a `.env` file in the project root directory to keep it secure and separate from the codebase. Create a new file named `.env` in the project root directory. 

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

## Running the Application

### Starting the Server

Once you've completed the setup steps above, you're ready to run the application. Make sure your virtual environment is activated, then start the Flask development server:

```bash
python app.py
```

On some systems, you might need to use `python3` instead of `python`. The server will start and you should see output similar to:

```
 * Running on http://127.0.0.1:5001
```

### Accessing the Application

Once the server is running, open your web browser and navigate to one of the following URLs:

- `http://localhost:5001`
- `http://127.0.0.1:5001`

You should see the RIQ Lab Matcher homepage. The server will continue running until you stop it by pressing `Ctrl+C` in the terminal where it's running.

## Using the Application

### Creating an Account

When you first access the application, you'll need to create an account to use most features. Click on "Sign Up" or navigate to `/signup` to create a new account. You'll be asked to provide:

- **Username**
- **Email**
- **Password**

After submitting the signup form, you'll be logged in automatically. 

### Logging In

If you already have an account, click "Login" or navigate to `/login` to access your account. Enter your email and password to log in. If you've forgotten your password, you can use the "Forgot Password" link to reset it via email.

### Browsing PIs

A core feature of RIQ is browsing the database of faculty members. Navigate to the "Browse Labs" page (accessible from the homepage or at `/general`) to see all available PIs. You can filter the results by:

- **University/School**: e.g. MIT, Harvard
- **Department**: e.g., Biology, Computer Science, Chemistry

Use the dropdown menus at the top of the page to apply filters. The results will update automatically to show only faculty members matching your selected criteria. Each PI card displays their name, affiliation, research interests, and other relevant information.

### Saving Favorite PIs

While you browse through PIs, you can save those that interest you to your account for access later. Click the "Save" button on any faculty member card to add them to your saved list. You can view all your saved PIs by navigating to the "Saved PIs" page (accessible from your account menu or at `/saved`). From there, you can remove PIs from your saved list if you change your mind.

### Uploading Your Resume

To utilize the AI-powered matching features, you should upload your resume. Navigate to the "Upload Resume" page (accessible from the account menu or at `/resume`) and select a PDF or DOCX file from your computer. The application will:

1. Store your resume file securely
2. Extract text from the resume for analysis
3. Use this information for AI-powered matching

You can upload multiple resumes, but only the most recent one will be used for matching purposes. The application validates file types and sizes to maximize performance.

### AI-Powered Lab Matching

Once you've uploaded a resume and completed your profile (including your concentration, year in school, and research interests), you can access the AI-powered matching feature. Use the "Matches" page (at `/matches`) to see personalized lab recommendations. The system analyzes:

- Your resume content and experience
- Your stated research interests
- Your preferred techniques and methods
- Your academic background and year in school

Based on this analysis, the AI generates a ranked list of compatible research labs, explaining why each match is a good fit for your profile. This feature requires a valid OpenAI API key to function.

### Drafting Emails to PIs

RIQ can generate personalized email drafts for contacting Principal Investigators. Go to the "Draft Email" page (at `/draft-email`) and:

1. Select a PI from your saved list or search for one
2. Customize the email tone and content
3. Click "Generate Email" to create a personalized draft

The AI will generate a professional email that:
- Introduces you and your background
- Explains why you're interested in their research
- Highlights relevant experience from your resume
- Requests a meeting or research opportunity

You can edit the generated email before copying it to your email client. The application also supports bulk email drafting for multiple PIs at once, accessible at `/bulk-email`.

### Comparing Labs

If you're deciding between multiple research opportunities, you can use the lab comparison feature (at `/compare-labs`). Select two or more PIs to compare side-by-side, viewing their research interests, techniques, publications, and other relevant information in a structured format to help you make an informed decision.

### Managing Your Account

Access your account settings by clicking on your username in the navigation bar or navigating to `/account`. On this page you can:

- View your account information
- Update your profile 
- Manage your saved PIs
- View your uploaded resumes
- Change your password

## Project Structure

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
---