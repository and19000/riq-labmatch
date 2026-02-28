# Answers to Clarifying Questions - RIQ LabMatch Codebase

**Date:** January 27, 2025  
**Purpose:** Answer questions about tech stack, database, auth, and matching system

---

## ✅ Answers to Your Questions

### 1. Tech Stack

| Component | Technology | Details |
|-----------|-----------|---------|
| **Backend** | Flask (Python) | Server-side rendering with HTML templates |
| **Frontend** | HTML Templates (Jinja2) | Not React/Next.js - server-side rendered |
| **ORM** | SQLAlchemy | Database abstraction layer |
| **Database** | SQLite (dev) / PostgreSQL (production) | Configured via `DATABASE_URL` env var |
| **Matching Engine** | Python | V2 (default), V3 (sophisticated), V1 (legacy) |

**Key Files:**
- Main app: `/Users/kerrynguyen/Projects/riq-labmatch/faculty_pipeline/app.py`
- Templates: `/Users/kerrynguyen/Projects/riq-labmatch/faculty_pipeline/templates/`

---

### 2. Database & Storage

#### Database Models (SQLAlchemy)
Located in `app.py`:

```python
# User accounts
class User(db.Model):
    id, username, email, password_hash, created_at

# Saved professors
class SavedPI(db.Model):
    id, user_id, pi_id, created_at

# Uploaded resumes
class Resume(db.Model):
    id, user_id, filename, file_path, resume_text, uploaded_at

# User profiles
class UserProfile(db.Model):
    id, user_id, major_field, year_in_school, looking_for, 
    top_techniques, onboarding_complete, profile_completeness

# Password reset tokens
class PasswordResetToken(db.Model):
    id, user_id, token, created_at, expires_at, used
```

#### Professor Storage
**Professors are NOT stored in database tables.** They are loaded from JSON files:

- **Primary file:** `data/faculty_working.json`
- **Pipeline output:** `output/harvard_university_20260120_162804.json`
- **Latest pipeline:** `output/harvard_university_20260127_134047_v532.json`

**Loading function:**
```python
def load_faculty():
    """Load all the faculty/PI data from our JSON file."""
    with open(FACULTY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
```

**Database Configuration:**
- Development: SQLite (`sqlite:///instance/riq.db`)
- Production: PostgreSQL (via `DATABASE_URL` env var)

---

### 3. Authentication System

**Type:** Custom Flask authentication (NOT Firebase/Supabase)

**Implementation:**
- Password hashing: Werkzeug `pbkdf2:sha256` (Python 3.9 compatible)
- Session management: Flask sessions with secure cookies
- Password reset: Token-based system stored in `PasswordResetToken` table

**Password Reset Flow:**
1. User requests reset at `/forgot-password`
2. System generates token, stores in `PasswordResetToken` table
3. Token expires after 1 hour
4. Email sent (or link shown in console if SMTP not configured)
5. User clicks link → `/reset-password/<token>`
6. User sets new password

**Files:**
- Password reset routes: `app.py` (lines ~600-700)
- Admin reset script: `reset_password_admin.py` (if exists)
- Documentation: `QUICK_PASSWORD_RESET.md`, `RESET_PASSWORD_GUIDE.md`

**Known Issue:** Password reset may not be working properly (needs fixing)

---

### 4. Matching Algorithm Location

#### Current Matching Algorithms

| Version | Location | Status | Default |
|---------|----------|--------|---------|
| **V1** | `/Users/kerrynguyen/Documents/riq-labmatch/app.py` | Legacy | No |
| **V2** | `/Users/kerrynguyen/Projects/riq-labmatch/services/matching/` | Current | ✅ Yes |
| **V3** | `/Users/kerrynguyen/Projects/riq-labmatch/services/matching/` | Newest | No |

#### V2 Matching (Current Default)

**Directory:** `/Users/kerrynguyen/Projects/riq-labmatch/services/matching/`

**Files:**
- `match.py` - Main entry point
- `scorer.py` - Deterministic scoring engine
- `extractor.py` - LLM-powered student profile extraction
- `embedding_service.py` - Embedding computation with caching
- `models.py` - Data models (StudentProfile, FacultyProfile, MatchResult)
- `api.py` - API wrapper for Flask integration
- `user_preferences.py` - User preferences collection

**Integration in app.py:**
```python
# Lines 33-44
try:
    from services.matching.api import MatchingAPI
    HAS_V3_MATCHING = True
except ImportError:
    HAS_V3_MATCHING = False
```

**Route:** `/matches` endpoint (lines ~1000-1156 in app.py)

**Algorithm Details:**
- **Scoring:** Deterministic (105 points total)
  - Research Interest Match: 40 points
  - Techniques & Skills: 25 points
  - Experience Level Fit: 15 points
  - Practical Fit: 10 points
  - Department Context: 5 points
  - Activity Signals: 5 points
  - Response Rate Bonus: 5 points

---

### 5. Professor Data Structure

**From Pipeline JSON:**
```json
{
  "id": "faculty_id",
  "name": "Professor Name",
  "h_index": 125,
  "research_topics": ["topic1", "topic2"],
  "department": "Computer Science",
  "website": "https://...",
  "email": "email@harvard.edu",
  "institution": "Harvard University",
  "openalex_id": "...",
  "orcid": "...",
  "works_count": 500,
  "cited_by_count": 10000
}
```

**Available Data:**
- ✅ Name, h_index, research_topics, department
- ✅ Website, email (from pipeline v5.3.2)
- ✅ OpenAlex ID, ORCID
- ✅ Publication counts, citations
- ✅ Research profile (topics, concepts, keywords)

**Research Profile Structure:**
- Topics (up to 15)
- Concepts (up to 10)
- Keywords (derived from topics/concepts)
- Fields (research domains)

---

### 6. Current Matching Implementation

**How It Works:**
1. Student uploads resume (PDF/DOCX)
2. System extracts text from resume
3. LLM extracts student profile (research interests, techniques, level)
4. System loads faculty from JSON file
5. Deterministic scoring matches student to each faculty
6. Top matches returned with explanations

**Matching Uses:**
- Research area overlap (keywords, topics, concepts)
- Technique alignment
- Experience level compatibility
- Department fit
- Research impact (h-index)

**NOT Currently Using:**
- Website scraping for research areas (uses OpenAlex data)
- Abstract analysis (uses research_topics from OpenAlex)

---

## Summary Table

| Question | Answer |
|----------|--------|
| **Tech Stack** | Flask (Python) + SQLAlchemy + HTML Templates (Jinja2) |
| **Database** | SQLite (dev) / PostgreSQL (production) via SQLAlchemy |
| **Auth System** | Custom Flask auth with Werkzeug password hashing |
| **Matching Code Location** | `/Users/kerrynguyen/Projects/riq-labmatch/services/matching/` |
| **Professor Storage** | JSON files (`data/faculty_working.json`), NOT database tables |
| **UI Framework** | Server-side HTML templates (NOT React/Next.js) |
| **Password Reset** | Token-based, stored in `PasswordResetToken` table (needs fixing) |

---

## Key Insights for Implementation

### 1. Professor Data Management
- **Current:** Professors loaded from JSON files
- **Recommendation:** Keep JSON-based approach OR migrate to database table
- **For new pipeline:** Update `faculty_working.json` with new data

### 2. Matching Algorithm
- **Current:** V2 is default (deterministic scoring)
- **V3 exists:** More sophisticated but not default
- **V1 exists:** Legacy, in separate app.py location
- **Recommendation:** Use V2 or V3, remove V1 if not needed

### 3. Password Reset
- **Current:** Token-based system exists
- **Issue:** May not be working properly
- **Fix needed:** Verify token generation, email sending, reset flow

### 4. UI Improvements
- **Current:** Server-side HTML templates
- **Not React/Next.js:** Keep this in mind for UI changes
- **Templates:** Located in `templates/` directory

---

## Next Steps

Based on these answers, I can now generate:

1. ✅ **Pipeline v5.3.3** - Improved pipeline with fixes
2. ✅ **Matching Algorithm Updates** - Research-based matching improvements
3. ✅ **Password Reset Fix** - Fix the password reset flow
4. ✅ **UI Improvements** - Enhance HTML templates
5. ✅ **Database Migration Script** - Optionally migrate professors to DB table

**Ready to proceed with implementation!**
