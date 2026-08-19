# Local real-backend acceptance

These instructions use an isolated SQLite database and temporary credentials supplied through environment variables. Never reuse pilot or production secrets.

## Backend

From `launch-circle-api/`:

```bash
export ACCEPTANCE_JWT_SECRET=GENERATE_A_TEMPORARY_RANDOM_VALUE
export ACCEPTANCE_TEST_PASSWORD=CHOOSE_A_TEMPORARY_TEST_PASSWORD
SQLITE_DATABASE_URL=sqlite:///./data/acceptance_phase0.db \
JWT_SECRET="$ACCEPTANCE_JWT_SECRET" \
DEVELOPMENT_AUTH_ENABLED=true \
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Generate the JWT value locally, for example with `openssl rand -hex 32`. Do not save either value in source control.

URLs:

- development host: `http://127.0.0.1:8000/`
- Android emulator: `http://10.0.2.2:8000/`
- physical phone: `http://HOST_LAN_IP:8000/`

Determine the current LAN address immediately before the phone build. The phone and development machine must be on the same LAN and TCP port 8000 must be reachable.

The reusable Phase 1 seed script also reads `ACCEPTANCE_TEST_PASSWORD`; `ACCEPTANCE_OPT_IN_URL` may be supplied when a specific test URL is required. It uses example.com identities and never prints the password.

## Development accounts

The isolated seed creates example-only Developer A and tester identities. Use the temporary password from `ACCEPTANCE_TEST_PASSWORD`. Delete or discard the acceptance database after testing; all `*.db` files are ignored by Git.

## Android acceptance builds

Emulator:

```bash
./gradlew testDebugUnitTest assembleDebug \
  -PlaunchCircleUseDemoRepository=false \
  -PlaunchCircleEnableDevelopmentAuth=true \
  -PlaunchCircleApiBaseUrl=http://10.0.2.2:8000/
```

Physical phone:

```bash
./gradlew testDebugUnitTest assembleDebug \
  -PlaunchCircleUseDemoRepository=false \
  -PlaunchCircleEnableDevelopmentAuth=true \
  -PlaunchCircleApiBaseUrl=http://HOST_LAN_IP:8000/
```

The debug manifest permits HTTP only for local testing. Development login is additionally gated by `BuildConfig.DEBUG` and cannot appear in a release build.

## Verified workflow

1. Developer A registers and creates a launch.
2. The cold-start dashboard remains useful below 12 testers.
3. Owner self-assignment and duplicate assignments are rejected.
4. Developer B confirms opt-in and installation.
5. Scheduled missions are generated and one mission plus factual feedback is completed.
6. Developer A observes updated tester, mission, and feedback state.
7. FastAPI restart preserves all SQLite records.
8. The Galaxy S10 repeats the real Android UI and backend flow.
