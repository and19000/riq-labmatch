# How to Access Your Website

## Quick Start

Your Flask server is currently running! Here's how to access it:

### Option 1: Using localhost (Recommended)
Open your web browser and go to:
```
http://localhost:5001
```

### Option 2: Using 127.0.0.1
Open your web browser and go to:
```
http://127.0.0.1:5001
```

**Note:** The server runs on port 5001 (not 5000) to avoid conflicts with macOS AirPlay service.

## If the Server Isn't Running

If you need to start the server, run these commands in your terminal:

```bash
cd /Users/kerrynguyen/Projects/riq-labmatch
source venv/bin/activate
python app.py
```

You should see:
```
 * Running on http://127.0.0.1:5001
```

Then open your browser to `http://localhost:5001`

## Troubleshooting

### Issue: "This site can't be reached" or "Connection refused"

1. **Check if the server is running:**
   ```bash
   lsof -ti:5001
   ```
   If nothing is returned, the server isn't running. Start it using the commands above.

2. **Check if port 5001 is being used by another application:**
   ```bash
   lsof -i:5001
   ```
   If another application is using port 5001, you may need to stop it or use a different port.

3. **Try a different browser:**
   Sometimes browser cache or extensions can cause issues. Try:
   - Chrome/Chromium
   - Firefox
   - Safari

4. **Clear your browser cache:**
   - Press `Cmd + Shift + R` (Mac) or `Ctrl + Shift + R` (Windows/Linux) to hard refresh

### Issue: Page loads but shows an error

Check the terminal where Flask is running for error messages. Common issues:
- Missing dependencies: Run `pip install -r requirements.txt`
- Database issues: The database should auto-create, but you can check `instance/riq.db` exists
- Missing data file: Check that `data/faculty.json` exists

### Issue: Server won't start

1. Make sure you're in the virtual environment:
   ```bash
   source venv/bin/activate
   ```
   You should see `(venv)` at the start of your terminal prompt.

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Check Python version (should be 3.9+):
   ```bash
   python --version
   ```

## Available Pages

Once you access the website at `http://localhost:5001`, you can navigate to:
- `/` - Home page
- `/login` - Login page
- `/signup` - Create a new account
- `/general` - Browse all faculty/PIs
- `/help` - Help page

## Stopping the Server

When you're done, stop the server by pressing `Ctrl + C` in the terminal where it's running.





