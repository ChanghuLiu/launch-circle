# Launch Circle: 12 Testers

Launch Circle helps Android developers find testers, complete a coordinated 14-day closed test, and prepare evidence for production access.

## Projects

- `launch-circle-api/` — FastAPI, SQLAlchemy, and SQLite backend
- `launch-circle-android/` — Kotlin and Jetpack Compose Android application

## Implemented

- development and Google identity flows with access/refresh tokens
- app launches, tester assignment, automatic matching, and replacements
- Day 1, 3, 5, 8, 11, and 14 testing missions
- feedback, tester health, readiness dashboards, and production summaries
- developer invites, join-by-code, and shared Google Group onboarding
- cold-start behavior below the 12-tester minimum
- single-instance HTTPS pilot deployment assets with persistent SQLite backups

Launch Circle records testing evidence and does not guarantee Google approval.

## Verification

The current baseline passes the backend test suite, Android unit tests, Android debug build, Phase 0/1 automated acceptance, and Galaxy S10 real-backend acceptance.

See `launch-circle-api/README.md` for local backend setup, `launch-circle-android/README.md` for Android configuration, and `PILOT_DEPLOYMENT.md` for the external HTTPS pilot procedure.
