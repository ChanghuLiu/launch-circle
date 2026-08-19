# Launch Circle API

FastAPI, SQLAlchemy, and SQLite backend for **Launch Circle: 12 Testers**.

## Capabilities

- Google identity exchange plus rotating refresh tokens
- debug-only email/password development authentication
- app launches, tester assignment, automatic matching, and replacement
- scheduled Day 1, 3, 5, 8, 11, and 14 missions
- feedback, tester health, readiness dashboards, and reports
- invite codes and Google Group setup confirmation
- persistent single-instance SQLite pilot operation

## Local setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Set a local-only JWT secret in `.env`, then run:

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
curl http://localhost:8000/health
```

Tables are created at startup. Local SQLite defaults to `data/launch_circle.db`.

## Google authentication

Create a Google OAuth Web client ID for backend token audience verification and set `GOOGLE_CLIENT_ID`. Android must use the same value as `googleServerClientId`. No OAuth client secret belongs in this repository or the APK.

## Checks

```bash
pytest -q
ruff check app tests scripts --select E4,E7,E9,F --ignore E402
```

For Android and real-backend acceptance instructions, see `../launch-circle-android/README.md` and `../launch-circle-android/ACCEPTANCE.md`.

For an external HTTPS pilot, follow `../PILOT_DEPLOYMENT.md`. The pilot remains a single FastAPI instance with persistent SQLite; PostgreSQL and Docker are not required.
