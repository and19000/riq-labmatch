# Deploy RIQ LabMatch MVP

Steps for cofounders to run and deploy the app locally or on a host (e.g. Render, Railway, or a VPS).

## 1. Clone and enter app directory

```bash
git clone https://github.com/and19000/riq-labmatch.git
cd riq-labmatch
```

(The repo root is the app: `app.py`, `templates/`, `data/`, etc.)

## 2. Python environment

- **Python 3.9+** required.

```bash
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Environment variables

```bash
cp .env.example .env
```

Edit `.env` and set at least:

- **SECRET_KEY** – required for sessions. Generate one:  
  `python3 -c "import secrets; print(secrets.token_hex(32))"`
- **OPENAI_API_KEY** – needed for AI email drafting (optional for matching only).

Other keys (e.g. Brave, OpenAlex) are only for the faculty pipeline, not for running the MVP app.

## 4. Run the app

**Option A – script (recommended)**

```bash
chmod +x LAUNCH_MVP.sh
./LAUNCH_MVP.sh
```

**Option B – manual**

```bash
export FLASK_ENV=development
export PORT=5001
python app.py
```

Then open: **http://localhost:5001**

- Sign up: http://localhost:5001/signup  
- After signup, complete the 5-question onboarding to see professor matches.

## 5. Faculty data (out of the box)

The app ships with **data/faculty_working.json**, so it runs without extra steps. Matching uses that file if no pipeline output is present.

To use the **full MVP set (1,500 faculty with email or website)**:

1. Obtain a pipeline output file named `harvard_university_*_v533.json` (from a pipeline run).
2. Run the filter script from `faculty_pipeline`:

   ```bash
   python scripts/filter_for_mvp.py
   ```

   This creates **output/harvard_mvp_1500.json**. Restart the app; it will prefer this file for matching.

(If `output/` doesn’t exist, create it or run the script once; it will create the file next to the pipeline JSON.)

## 6. Production deployment (e.g. Render)

- Set **Build Command**: `pip install -r requirements.txt` (or use a `render.yaml` if you have one).
- Set **Start Command**: `gunicorn -b 0.0.0.0:$PORT app:app`
- In the dashboard, add env vars: **SECRET_KEY**, **OPENAI_API_KEY** (if needed), and optionally **DATABASE_URL** for Postgres (the app supports SQLite by default).

The repo includes a **Procfile** and **render.yaml** in `faculty_pipeline/` if your host uses them.

## 7. Optional: restrict access

To limit sign-in to specific emails (e.g. beta testers):

- Set **ALLOWED_USERS** in `.env` or in the host’s env to a comma-separated list, e.g.  
  `user1@example.com,user2@example.com`
- Only those addresses can log in; others see “Access denied.”

---

**Summary:** Clone → `cd faculty_pipeline` → venv + `pip install -r requirements.txt` → copy `.env.example` to `.env` and set `SECRET_KEY` → run `./LAUNCH_MVP.sh` or `python app.py`. App works with bundled `data/faculty_working.json`; optionally add `output/harvard_mvp_1500.json` for the full MVP faculty set.
