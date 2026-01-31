# MVP 5-Question Profile – Database Migration

The MVP uses 5 new fields on `UserProfile`. Add them with a migration or recreate the DB.

## Option 1: Flask-Migrate (recommended)

From `faculty_pipeline/`:

```bash
export FLASK_APP=app.py
flask db migrate -m "Add 5-question profile fields (research_field, research_topics, academic_level, work_style, needs_funding)"
flask db upgrade
```

## Option 2: Recreate DB (MVP / dev only)

If you don't use migrations or are fine resetting:

1. Delete the SQLite DB: `rm -f instance/riq.db` (from `faculty_pipeline/`).
2. Start the app; `init_db()` will create tables with the new columns.

Existing users will need to complete onboarding again (5 questions).
