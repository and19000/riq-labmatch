# GitHub Push Instructions

## Step 1: Connect to Existing Repository (Andrew Dou's Repo)

**IMPORTANT:** Andrew Dou has already created the GitHub repository. We need to connect to it.

### Option A: If you know the repository URL

```bash
cd /Users/kerrynguyen/Projects/riq-labmatch/faculty_pipeline

# Add remote (replace with actual repository URL from Andrew)
git remote add origin https://github.com/ANDREW_DOU_USERNAME/riq-labmatch-pipeline.git

# Or if using SSH:
# git remote add origin git@github.com:ANDREW_DOU_USERNAME/riq-labmatch-pipeline.git

# Check remote
git remote -v

# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

### Option B: If repository doesn't exist yet

Ask Andrew Dou for:
1. The GitHub repository URL
2. Or create it at: https://github.com/new
   - Repository name: `riq-labmatch-pipeline`
   - Set to Private (recommended)
   - Don't initialize with README

Then use Option A above.

## Step 3: Add Collaborators

1. Go to repository Settings → Collaborators
2. Click "Add people"
3. Add co-founders by GitHub username or email
4. They'll receive an invite to accept

## Step 4: Verify

Check that files are on GitHub:
- ✅ README.md
- ✅ requirements.txt
- ✅ .gitignore
- ✅ faculty_pipeline_v4_4.py
- ✅ faculty_pipeline_v4_5.py
- ✅ faculty_pipeline_v4_5_1_restore.py
- ✅ Documentation files

## What's NOT Pushed (by design)

These are in `.gitignore` and won't be pushed:
- `output/*` - Large data files
- `checkpoints/*` - Checkpoint files
- `*.log` - Log files
- `.env` - Environment variables

---

**After pushing, share the repository URL with your co-founders!**
