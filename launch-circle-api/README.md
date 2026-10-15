# Launch Circle API

FastAPI, SQLAlchemy, and SQLite backend for **Launch Circle: 12 Testers**.

## Capabilities

- Google identity exchange plus rotating refresh tokens
- debug-only email/password development authentication
- app launches, tester assignment, automatic matching, and replacement
- scheduled Day 1, 3, 5, 8, 11, and 14 missions
- feedback, tester health, readiness dashboards, and reports
- invite codes and Google Group setup confirmation
- Google Play purchase verification, additional-app entitlements, and same-app Managed credits
- tester workload tracking and Managed Launch offers
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

Google Play Billing is the only supported payment channel. Configure `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` in the protected server environment, or use Workload Identity Federation by setting `GOOGLE_APPLICATION_CREDENTIALS` to Google's external-account credential configuration file. The latter contains no private key and uses the server's workload identity. Configure `GOOGLE_PLAY_DEVELOPER_ACCOUNT_ID` to the canonical numeric publisher account ID. Before granting the first-app entitlement, the backend checks that the submitted account ID matches this server setting and that the configured Publisher API identity can read the app's Play review record. This is a read-only ownership check; it does not create an edit or change Play metadata. Configure the three one-time products in Play Console. The backend verifies each purchase with the Android Publisher API before granting an entitlement or redeeming a credit. See `../PILOT_DEPLOYMENT.md` for product IDs, price requirements, and setup.

## Checks

```bash
pytest -q
ruff check app tests scripts --select E4,E7,E9,F --ignore E402
```

For Android and real-backend acceptance instructions, see `../launch-circle-android/README.md` and `../launch-circle-android/ACCEPTANCE.md`.

For an external HTTPS pilot, follow `../PILOT_DEPLOYMENT.md`. The pilot remains a single FastAPI instance with persistent SQLite; PostgreSQL and Docker are not required.
