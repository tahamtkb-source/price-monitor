
# Price Monitor - Prototype

This package contains a simple Flask app that scrapes retail sites (prototype),
stores results in SQLite, and exposes a small dashboard and API.

## Quick start (local)

1. python3 -m venv venv
2. source venv/bin/activate   (Windows: venv\Scripts\activate)
3. pip install -r requirements.txt
4. python app.py
5. Open http://127.0.0.1:5000

## Deploy to Render

1. Create a GitHub repo and push these files.
2. Sign up at https://render.com and connect GitHub.
3. New → Web Service → choose repo.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn -w 4 app:app`
6. Deploy.

## Notes

- This is a prototype. For production use:
  - Replace SQLite with Postgres (managed DB).
  - Harden per-site parsers and respect site TOS.
  - Throttle scrapes and consider proxies for scale.
