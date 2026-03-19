import os

from backend.app import app, db, env


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    port = int(os.getenv("PORT", 5001))
    debug_mode = env != "production"
    app.run(debug=debug_mode, host="0.0.0.0", port=port)

