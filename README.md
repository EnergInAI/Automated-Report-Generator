# EnergInAI Mini Report Generator

Login-protected web form → enter details from the customer's electricity bill → download the PDF mini report.

## Run locally
```bash
pip install -r requirements.txt
playwright install chromium
USERS="alice:secret1" SESSION_SECRET=anything INSECURE_COOKIES=1 uvicorn app:app --port 8000
```
Open http://127.0.0.1:8000 (`INSECURE_COOKIES=1` is only for local http).

## Tests
```bash
pip install -r requirements-dev.txt && playwright install chromium
python -m pytest -q
```

## Deploy on Render (free)
1. Render → New → Blueprint → select this repo (uses `render.yaml` + `Dockerfile`).
2. Set the `USERS` env var: comma-separated `username:password` pairs, e.g. `alice:Pass123,bob:Pass456`.
3. Deploy. To add/remove a login later, edit `USERS` in the Render dashboard.

Free instances sleep after ~15 min idle; the first visit after that takes ~30-60 s to wake up.
