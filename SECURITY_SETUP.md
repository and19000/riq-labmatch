# Security Setup - API Keys Configuration

**⚠️ CRITICAL: API keys are now stored in `.env` file for security.**

---

## ✅ Security Measures Implemented

1. **`.env` file created** - Contains all API keys (NOT committed to git)
2. **`.env.example` created** - Template for team members (safe to commit)
3. **`.gitignore` updated** - Ensures `.env` is never committed
4. **Shell scripts updated** - Now load from `.env` instead of hardcoding
5. **Documentation updated** - Removed hardcoded keys from examples

---

## Setup Instructions

### Step 1: Create Your .env File

```bash
cd /Users/kerrynguyen/Projects/riq-labmatch/faculty_pipeline

# Copy the template
cp .env.example .env

# Edit .env and fill in your actual API keys
# Use a text editor to open .env
```

### Step 2: Fill in Your API Keys

Edit `.env` file with your actual keys:

```bash
# OpenAI API Key (for matching algorithm)
OPENAI_API_KEY=sk-your-actual-openai-key-here

# Brave Search API Key (for website discovery)
BRAVE_API_KEY=your-actual-brave-key-here

# OpenAlex Contact Email
OPENALEX_CONTACT_EMAIL=riqlabmatch@gmail.com

# Flask Secret Key (generate a secure one)
SECRET_KEY=your-generated-secret-key-here
```

### Step 3: Generate Secure Secret Key

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as `SECRET_KEY` in your `.env` file.

---

## Verification

### Check .env is NOT in Git

```bash
git status
# .env should NOT appear in the list
```

### Check .env is in .gitignore

```bash
grep "\.env$" .gitignore
# Should output: .env
```

### Test Loading Environment Variables

```bash
# Source the .env file
source .env

# Verify keys are loaded (don't print full keys!)
echo "OPENAI_API_KEY is set: $([ -n "$OPENAI_API_KEY" ] && echo 'YES' || echo 'NO')"
echo "BRAVE_API_KEY is set: $([ -n "$BRAVE_API_KEY" ] && echo 'YES' || echo 'NO')"
```

---

## Updated Scripts

All shell scripts now load from `.env`:

- ✅ `keep_running.sh` - Loads from .env
- ✅ `resume_pipeline.sh` - Loads from .env
- ✅ `monitor_pipeline.sh` - Loads from .env
- ✅ `run_test_v4_3.sh` - Loads from .env

**No more hardcoded API keys in scripts!**

---

## For Team Members

1. **Clone the repository**
2. **Copy `.env.example` to `.env`**
3. **Fill in your API keys in `.env`**
4. **Never commit `.env` to git**

```bash
git clone https://github.com/and19000/riq-labmatch.git
cd riq-labmatch/faculty_pipeline
cp .env.example .env
# Edit .env with your keys
```

---

## Security Checklist

- [x] `.env` file created with API keys
- [x] `.env.example` template created (safe to commit)
- [x] `.env` in `.gitignore` (verified)
- [x] Hardcoded keys removed from shell scripts
- [x] Hardcoded keys removed from documentation
- [x] Scripts updated to load from `.env`

---

## Important Notes

1. **NEVER commit `.env`** - It contains sensitive keys
2. **DO commit `.env.example`** - It's a safe template
3. **Rotate keys if exposed** - If a key is accidentally committed, rotate it immediately
4. **Use different keys per environment** - Dev vs Production
5. **Limit key permissions** - Only grant necessary API permissions

---

**Status:** ✅ **SECURITY SETUP COMPLETE**
