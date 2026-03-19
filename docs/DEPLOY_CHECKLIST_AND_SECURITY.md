# RIQ LabMatch – Deploy Checklist, Security & Admin

Use this before your partner renders the site under a custom domain and when locking down production.

---

## 1. Before going live (pre-launch)

### Domain & Render

- [ ] **Custom domain on Render**  
  In Render: Service → Settings → Custom Domain. Add your domain (e.g. `labmatch.yourapp.com`). Render will show DNS records (CNAME or A).
- [ ] **DNS**  
  At your registrar (GoDaddy, Namecheap, etc.): add the CNAME or A record Render gives you. Wait for propagation (up to 48h, often minutes).
- [ ] **HTTPS**  
  Render provisions SSL for the custom domain. Ensure the app is only used over `https://` (no `http://` for production).

### Environment variables (Render dashboard)

Set these in Render → Service → Environment (do **not** commit real values to git):

| Variable | Required for production | Notes |
|----------|--------------------------|--------|
| `FLASK_ENV` | Yes | Set to `production` (Render may set this already). |
| `SECRET_KEY` | **Critical** | Long random string (e.g. 32+ chars). Render can “Generate” one; store it securely. |
| `DATABASE_URL` | Yes | Usually auto-set by Render if you attach a Postgres DB. |
| `OPENAI_API_KEY` | Optional | Needed for AI matching fallback and email drafting. |
| `USE_MATCHING_V2` | Optional | `true` (default) or `false`. |
| `ALLOWED_USERS` | Optional | Comma-separated list of emails allowed to sign up. Leave empty to allow all. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `FROM_EMAIL` | Optional | For password-reset and any transactional email. Use app password, not main email password. |

### Database

- [ ] **Migrations**  
  If you use Flask-Migrate, run migrations against the production DB (e.g. via Render shell or a one-off job) so tables match the code.
- [ ] **Create tables**  
  The app also calls `db.create_all()` on startup, which creates missing tables. Prefer migrations for schema changes.

### App behavior

- [ ] **Resume/file uploads**  
  On Render, disk is often ephemeral. For production, plan to store uploads in external storage (e.g. S3) and set `UPLOAD_FOLDER` or switch to a cloud path. Until then, assume uploads may be lost on redeploy.
- [ ] **Matching data**  
  Confirm faculty/matching data is loaded from the right paths (e.g. bundled in repo or a read-only asset the app can read at runtime).

---

## 2. Security checklist

### Already in place

- **Passwords:** Stored as hashes (pbkdf2:sha256), not plain text.
- **Sessions:** `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE = Lax`; in production `SESSION_COOKIE_SECURE = True` (HTTPS only).
- **Secret key:** Must be set in production via `SECRET_KEY` env var (no default in prod).
- **Password reset:** Time-limited tokens, single use.

### Must do / reinforce

1. **SECRET_KEY**  
   In production, never run without a strong, unique `SECRET_KEY` in the environment. If missing, the app falls back to a dev default; fix that before going live.

2. **HTTPS only**  
   Custom domain on Render should be used only over HTTPS. Avoid redirecting production traffic to `http://`.

3. **API keys**  
   Keep `OPENAI_API_KEY` (and any Brave/OpenAlex keys) only in env vars, never in code or in git.

4. **Database**  
   Use a dedicated Postgres DB; keep `DATABASE_URL` secret and only in env. Restrict DB access (e.g. IP allowlist if your host supports it).

5. **ALLOWED_USERS (optional)**  
   If you want restricted signups, set `ALLOWED_USERS` to a comma-separated list of allowed emails. Only those users can register.

6. **File uploads**  
   The app uses `secure_filename`; ensure upload dir is not directly web-accessible (no static serving of `UPLOAD_FOLDER`). For production, move to S3 or similar and avoid storing sensitive files on local disk.

7. **Dependencies**  
   Run `pip install -r requirements.txt` and periodically update dependencies and fix known vulnerabilities (`pip audit` or similar).

---

## 3. Tracking user activity – admin dashboard

Yes, you should use an **admin dashboard** (or at least admin-only routes) to view and track user activity. That keeps tracking in one place and behind access control.

### What to track (examples)

- **Users:** Signups (username, email, `created_at`).
- **Engagement:** Saved PIs per user, number of matches views, resume uploads (e.g. count or last date).
- **Actions:** Use of “draft email” or “bulk email” (e.g. counts or last used), matches page visits.
- **Optional:** Login timestamps (requires a small “login event” or “last login” model or column).

You can start with **read-only** reporting: no need to let admins edit or delete user data unless you explicitly want that.

### How to secure the admin section

1. **Admin-only access**  
   - Add an env var, e.g. `ADMIN_EMAILS`, with comma-separated emails (e.g. you and your partner).
   - In the app, define a decorator (e.g. `@admin_required`) that:
     - Requires the user to be logged in.
     - Checks that `current_user.email` is in `ADMIN_EMAILS`.
   - Apply this decorator to every admin route (e.g. `/admin`, `/admin/users`, `/admin/activity`).

2. **Routes to add (suggested)**  
   - `GET /admin` – Dashboard summary (total users, total saved PIs, recent signups).
   - `GET /admin/users` – List users (id, username, email, created_at, count of saved PIs, last activity if you store it).
   - `GET /admin/activity` – Optional: table or list of “recent activity” (e.g. last 50 saved-PI adds, last 20 match-page views) if you add a simple activity or event table.

3. **Data source**  
   Use existing models: `User`, `SavedPI`, `Resume`, `UserProfile`. You can add an `ActivityLog` or `UserEvent` model later if you want finer-grained events (e.g. “viewed matches”, “clicked draft email”).

4. **No sensitive data on the dashboard**  
   Do not show passwords, resume text, or tokens. Show only what’s needed for product/usage insight (counts, dates, emails if necessary for support).

### Summary

- **Before domain go-live:** Set domain in Render, DNS, env vars (`FLASK_ENV`, `SECRET_KEY`, `DATABASE_URL`, etc.), and run DB migrations if needed.
- **Security:** Strong `SECRET_KEY`, HTTPS only, env-only secrets, optional `ALLOWED_USERS`, safe upload handling, and updated dependencies.
- **Tracking:** Implement an admin dashboard (or admin-only pages) protected by `ADMIN_EMAILS`, and use it to view user counts, signups, saved PIs, and optionally other activity once you add minimal logging or an activity model.

If you want, the next step is to add a minimal `/admin` route and an `ADMIN_EMAILS` check in `app.py`, plus a simple admin template that lists users and saved-PI counts.
