# Incomplete / Non-Functional Features in RIQ Lab Matcher

This document lists all features that are implemented in the UI but don't fully work or are incomplete.

## 🔴 Critical Issues (Features Users Expect to Work)

### 1. **Password Reset Email** ❌
**Status:** Partially implemented, requires configuration

**Location:** `app.py` lines 287-360

**Issue:**
- Password reset functionality exists but **requires SMTP email configuration**
- Needs these environment variables:
  - `SMTP_SERVER` (defaults to `smtp.gmail.com`)
  - `SMTP_PORT` (defaults to `587`)
  - `SMTP_USERNAME` (required)
  - `SMTP_PASSWORD` (required)
  - `FROM_EMAIL` (optional, defaults to SMTP_USERNAME)

**Current Behavior:**
- If SMTP not configured, it prints the reset link to console/logs
- User never receives the email
- In production on Render, this means password reset is **completely broken**

**Fix Required:**
- Configure SMTP settings in Render environment variables, OR
- Use a service like SendGrid, Mailgun, or AWS SES
- Alternative: Use a service like Resend or Postmark for easier setup

**Code Reference:**
```python
# Line 321-327: Falls back to console print if SMTP not configured
if not smtp_username or not smtp_password:
    print(f"PASSWORD RESET EMAIL (SMTP not configured - showing link here):")
    print(f"Reset Link: {reset_link}")
    return True  # User thinks email was sent, but it wasn't
```

---

### 2. **Resume Text Extraction** ❌
**Status:** Placeholder - doesn't extract text from files

**Location:** `app.py` lines 784-787

**Issue:**
- Resume upload accepts PDF and DOCX files
- **Does NOT extract text from the files**
- Stores empty string `""` in `resume_text` field
- AI matching still works but uses placeholder text: "Resume uploaded but text extraction pending"

**Current Behavior:**
```python
# Line 787: Placeholder comment
resume_text = ""  # Placeholder - would extract actual text here
```

**Fix Required:**
- Install libraries: `PyPDF2` or `pdfplumber` for PDFs, `python-docx` for DOCX
- Implement text extraction function
- Extract and store text in `resume_text` field

**Impact:**
- AI matching works but is less accurate without actual resume content
- Email drafting can't reference specific resume details

**Code Reference:**
```python
# Line 785-787
# Note: This is a placeholder - in production you'd use libraries like PyPDF2 or python-docx
# to actually extract the text from PDFs and Word documents
resume_text = ""  # Placeholder - would extract actual text here
```

---

## 🟡 Medium Priority Issues

### 3. **Feedback Form** ⚠️
**Status:** Works but not useful in production

**Location:** `app.py` lines 1163-1177

**Issue:**
- Feedback form writes to `feedback_log.txt` file
- On Render (and most cloud platforms), file system is **ephemeral**
- Files are lost when service restarts or redeploys
- No way to actually read/access the feedback

**Current Behavior:**
```python
# Line 1174-1175: Writes to local file
with open("feedback_log.txt", "a") as f:
    f.write(f"[{datetime.now()}] User: {user_id}, Page: {page_context}\n{feedback_text}\n\n")
```

**Fix Required:**
- Store feedback in database (create Feedback model)
- OR send feedback via email
- OR integrate with external service (e.g., Google Forms, Typeform)
- OR use a logging service (e.g., Sentry, Logtail)

**Impact:**
- Users can submit feedback but it's lost
- No way to track user issues or suggestions

---

### 4. **Export Report PDF Generation** ⚠️
**Status:** Uses browser print, not actual PDF generation

**Location:** `app.py` lines 1180-1201, `templates/export_report.html`

**Issue:**
- "Export Report" button uses browser's `window.print()` function
- Not a real PDF generation library
- Comment in code says: "In production, use a library like reportlab or weasyprint for PDF"

**Current Behavior:**
- User clicks "Print / Save as PDF"
- Browser print dialog opens
- User must manually save as PDF
- Not a true "download PDF" feature

**Fix Required:**
- Install `reportlab` or `weasyprint` library
- Generate actual PDF file server-side
- Return PDF as download

**Impact:**
- Feature works but not as user-friendly as expected
- Requires manual browser interaction

**Code Reference:**
```python
# Line 1200: Comment indicates this is a placeholder
# For now, return a simple text version
# In production, use a library like reportlab or weasyprint for PDF
return render_template("export_report.html", ...)
```

---

## 🟢 Low Priority / Minor Issues

### 5. **File Upload Storage** ⚠️
**Status:** Works but ephemeral on cloud platforms

**Location:** `app.py` line 147, upload handling

**Issue:**
- Uploaded resumes stored in `uploads/` folder
- On Render/Railway, file system is ephemeral
- Files lost on restart/redeploy

**Current Behavior:**
- Files work fine locally
- In production, files may disappear

**Fix Required:**
- Use cloud storage (AWS S3, Google Cloud Storage, Cloudinary)
- Store file URLs in database instead of local paths

**Impact:**
- Users may lose uploaded resumes if service restarts

---

## Summary

### Features That Don't Work At All:
1. ❌ **Password Reset Email** - Requires SMTP configuration
2. ❌ **Resume Text Extraction** - Placeholder code only

### Features That Work But Are Not Production-Ready:
3. ⚠️ **Feedback Form** - Writes to ephemeral file
4. ⚠️ **Export Report PDF** - Uses browser print, not real PDF
5. ⚠️ **File Upload Storage** - Ephemeral on cloud platforms

### Recommended Fix Priority:
1. **HIGH:** Password Reset Email (critical for user experience)
2. **HIGH:** Resume Text Extraction (core feature accuracy)
3. **MEDIUM:** Feedback Form (user communication)
4. **MEDIUM:** Export Report PDF (user expectation)
5. **LOW:** File Upload Storage (works but not persistent)

---

## Quick Fix Checklist

- [ ] Configure SMTP for password reset emails
- [ ] Install and implement PDF/DOCX text extraction
- [ ] Move feedback to database or email
- [ ] Implement real PDF generation for export
- [ ] Move file uploads to cloud storage

