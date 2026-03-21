# RIQ LabMatch — Chrome shortcut (MV3)

Unpacked extension that opens your local Flask app when you click the toolbar icon.

## Load in Chrome

1. Start the app: from repo root, `source .venv/bin/activate && python run.py`
2. Chrome → **Extensions** → enable **Developer mode**
3. **Load unpacked** → choose this folder: `riq-labmatch/chrome-extension`
4. Pin the extension if you like; click the icon to open `http://127.0.0.1:5001/`

## Different port

Edit `background.js` and set `LABMATCH_DEV_URL` to match your `PORT` in `.env`.
