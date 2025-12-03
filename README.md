# RIQ Lab Matcher

A Flask-based web application for matching students with research opportunities (Principal Investigators/PIs) at various universities.

## Features

- **User Authentication**: Sign up, login, and account management
- **Faculty Database**: Browse faculty members by school and department
- **Save PIs**: Save favorite Principal Investigators to your account
- **Resume Upload**: Upload PDF or DOCX resumes for future AI matching
- **Email Drafting**: Draft emails to PIs (coming soon)
- **OpenAI Integration**: AI-powered features for matching and email generation

## Project Structure

```
riq-labmatch/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── data/
│   └── faculty.json      # Faculty/PI data
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── signup.html
│   ├── account.html
│   ├── general.html
│   ├── saved_pis.html
│   ├── resume_upload.html
│   ├── draft_email.html
│   └── help.html
├── static/
│   └── css/
│       └── style.css
├── instance/             # Database files (gitignored)
│   └── riq.db
├── uploads/             # Uploaded resumes (gitignored)
└── venv/                # Virtual environment (gitignored)
```

## Setup Instructions

### 1. Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

### 2. Clone the Repository

```bash
cd /Users/kerrynguyen/Projects/riq-labmatch
```

### 3. Create Virtual Environment (if not already created)

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

**Note**: The `.env` file is gitignored for security.

### 6. Initialize the Database

The database will be created automatically when you first run the app. If you need to recreate it:

```bash
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 7. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Routes

- `/` - Home page
- `/login` - User login
- `/signup` - User registration
- `/logout` - User logout
- `/account` - User account page
- `/general` - Browse faculty with filters (school, department)
- `/saved` - View saved PIs
- `/save-pi/<pi_id>` - Save a PI to your account (POST)
- `/resume` - Upload resume
- `/draft-email` - Draft email to PI
- `/help` - Help page
- `/test-gpt` - Test OpenAI API connection

## Database Models

### User
- `id`: Primary key
- `email`: Unique email address
- `password_hash`: Hashed password
- `created_at`: Account creation timestamp

### SavedPI
- `id`: Primary key
- `user_id`: Foreign key to User
- `pi_id`: Faculty member ID from faculty.json
- `created_at`: Save timestamp

## Development Notes

- The app uses SQLite for the database (stored in `instance/riq.db`)
- OpenAI GPT-4.1-mini is configured as the default model
- File uploads are restricted to PDF and DOCX formats
- The secret key should be changed in production (currently set to "dev-secret-change-later")

## Next Steps / TODO

- [ ] Implement AI-powered matching algorithm
- [ ] Complete email drafting functionality
- [ ] Add resume parsing and analysis
- [ ] Improve UI/UX
- [ ] Add more filtering options
- [ ] Implement search functionality
- [ ] Add email sending capability


