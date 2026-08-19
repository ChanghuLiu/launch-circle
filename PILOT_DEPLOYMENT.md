# Launch Circle external pilot deployment

This is a single-host pilot layout. Caddy terminates HTTPS and proxies only to Uvicorn on `127.0.0.1:8000`; FastAPI uses one persistent SQLite database. The database and backup directories are never served by Caddy.

## Required values

Copy `launch-circle-api/deploy/launch-circle.env.example` to `/etc/launch-circle/launch-circle.env` and set:

- `APP_ENV=pilot`
- `SQLITE_DATABASE_URL=sqlite:////var/lib/launch-circle/launch_circle.db`
- `JWT_SECRET`: unique random value of at least 16 characters; never reuse acceptance or development values
- `CORS_ORIGINS`: comma-separated HTTPS browser origins, or empty for the Android-only pilot; never `*`
- `PUBLIC_BASE_URL`: externally reachable HTTPS API origin
- `GOOGLE_GROUP_EMAIL=launch-circle-12-testers@googlegroups.com`
- `GOOGLE_GROUP_URL=https://groups.google.com/g/launch-circle-12-testers`
- `INVITE_BASE_URL=https://launchcircle.app/join` (future public link shape; direct code entry remains available)
- `DEVELOPMENT_AUTH_ENABLED=false`
- `GOOGLE_CLIENT_ID`: Google OAuth Web client ID when available

Pilot startup deliberately fails if the JWT secret is unchanged, the database path is relative, development auth is enabled, the public URL is not HTTPS, or CORS contains a wildcard.

## Ubuntu installation

### 1. Create the service account and directories

```bash
sudo useradd --system --home-dir /opt/launch-circle --create-home --shell /usr/sbin/nologin launch-circle
sudo install -d -o launch-circle -g launch-circle -m 0750 /opt/launch-circle /var/lib/launch-circle
sudo install -d -o launch-circle -g launch-circle -m 0700 /var/backups/launch-circle
sudo install -d -o root -g launch-circle -m 0750 /etc/launch-circle
```

### 2. Install the application

Place this source tree at `/opt/launch-circle`, with the backend at `/opt/launch-circle/launch-circle-api`. Use a reviewed release archive or secure copy from the development machine. Do not copy `.env`, acceptance databases, seeded data, APK signing files, or local credentials.

```bash
sudo chown -R launch-circle:launch-circle /opt/launch-circle
sudo -u launch-circle python3 -m venv /opt/launch-circle/venv
sudo -u launch-circle /opt/launch-circle/venv/bin/pip install /opt/launch-circle/launch-circle-api
```

### 3. Configure the environment

```bash
sudo install -o root -g launch-circle -m 0640 launch-circle-api/deploy/launch-circle.env.example /etc/launch-circle/launch-circle.env
sudoedit /etc/launch-circle/launch-circle.env
```

Generate the real JWT value on the server with `openssl rand -hex 32` and place only the result in the protected environment file. The example intentionally contains no secret.

For Google OAuth, create an OAuth 2.0 Web client for the backend token audience and set its client ID as `GOOGLE_CLIENT_ID`. Configure the Android OAuth client for package `com.launchcircle.testers` and the signing certificate SHA-1. Pass the same Web client ID to the Android `googleServerClientId` Gradle property. No client secret belongs in the APK. Infrastructure can start before these OAuth credentials exist, but external sign-in will return a configuration error until they are supplied.

### 4. Initialize or preserve SQLite

The service safely creates the parent and database on first start. Existing pilot upgrades must leave `/var/lib/launch-circle/launch_circle.db` in place. SQLite uses foreign keys, WAL mode, a 30-second busy timeout, and one Uvicorn process for the pilot.

Install the unit:

```bash
sudo install -o root -g root -m 0644 launch-circle-api/deploy/launch-circle-api.service /etc/systemd/system/launch-circle-api.service
```

### 5. Configure HTTPS with Caddy

Install Caddy using its official Ubuntu package instructions, then install the template:

```bash
sudo install -o root -g root -m 0644 launch-circle-api/deploy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl edit caddy
```

Add the real hostname to the Caddy service override:

```ini
[Service]
Environment=PILOT_HOST=api.your-domain.example
```

Point DNS for that hostname to the server before requesting a certificate. The template enables reverse proxying only; it does not enable file serving or directory listing.

### 6. Install the backup timer

```bash
sudo install -o root -g root -m 0644 launch-circle-api/deploy/launch-circle-backup.service /etc/systemd/system/launch-circle-backup.service
sudo install -o root -g root -m 0644 launch-circle-api/deploy/launch-circle-backup.timer /etc/systemd/system/launch-circle-backup.timer
sudo systemctl daemon-reload
sudo systemctl enable --now launch-circle-backup.timer
```

The backup command uses the SQLite online backup API, verifies the copy, creates a UTC timestamped file, and retains 14 files by default. It never copies over the live database.

### 7. Start and verify

```bash
sudo systemctl enable --now launch-circle-api
sudo systemctl restart caddy
curl -fsS https://api.your-domain.example/health
```

Expected response:

```json
{"status":"ok"}
```

The development `/auth/register` and `/auth/login` routes return 404 in pilot mode. No test-clock, reset, or seed routes are registered. Google OAuth remains at `/v1/auth/google`.

## Operations

```bash
sudo systemctl start launch-circle-api
sudo systemctl stop launch-circle-api
sudo systemctl restart launch-circle-api
sudo journalctl -u launch-circle-api -n 200 --no-pager
sudo journalctl -u caddy -n 200 --no-pager
sudo systemctl start launch-circle-backup.service
sudo journalctl -u launch-circle-backup.service -n 100 --no-pager
sudo -u launch-circle sqlite3 /var/lib/launch-circle/launch_circle.db "PRAGMA integrity_check;"
```

Database: `/var/lib/launch-circle/launch_circle.db`

Backups: `/var/backups/launch-circle/`

A cron alternative, if timers are unavailable, is a root-installed daily entry that runs as the service user:

```cron
17 3 * * * launch-circle cd /opt/launch-circle/launch-circle-api && /opt/launch-circle/venv/bin/python scripts/backup_sqlite.py
```

### Upgrade procedure

1. Run and verify an on-demand backup.
2. Stop `launch-circle-api`.
3. Replace only reviewed application files; preserve the environment, database, and backup directories.
4. Update the virtual environment with `/opt/launch-circle/venv/bin/pip install /opt/launch-circle/launch-circle-api`.
5. Start the service and inspect journal logs.
6. Verify `/health`, run `PRAGMA integrity_check`, and exercise sign-in plus one read-only app request.
7. Roll back application files if needed; do not overwrite the live database with an unverified copy.

## Android pilot configuration

All URLs must retain the trailing slash required by Retrofit.

Emulator against a local backend:

```bash
./gradlew assembleDebug -PlaunchCircleApiBaseUrl=http://10.0.2.2:8000/ -PlaunchCircleUseDemoRepository=false -PlaunchCircleEnableDevelopmentAuth=true
```

Galaxy on the local LAN:

```bash
./gradlew assembleDebug -PlaunchCircleApiBaseUrl=http://HOST_LAN_IP:8000/ -PlaunchCircleUseDemoRepository=false -PlaunchCircleEnableDevelopmentAuth=true
```

Private external-pilot rehearsal with Google OAuth configured:

```bash
./gradlew assembleDebug -PlaunchCircleApiBaseUrl=https://api.your-domain.example/ -PlaunchCircleUseDemoRepository=false -PlaunchCircleEnableDevelopmentAuth=false -PgoogleServerClientId=WEB_CLIENT_ID.apps.googleusercontent.com
```

Release builds override `USE_DEMO_REPOSITORY=false` and `ENABLE_DEVELOPMENT_AUTH=false` regardless of local Gradle properties. This task does not sign or publish an AAB.

## External-phone check

1. Disable Wi-Fi on the phone so the request uses the public network.
2. Open `https://api.your-domain.example/health` in the phone browser and verify the JSON response and trusted certificate.
3. Install the private rehearsal APK, sign in with an allowed Google pilot account, and verify My Launches refreshes.
4. Enter an invite code directly in the app. The future `launchcircle.app/join/...` website is not required for the pilot.
5. Confirm logs show HTTPS proxy requests and no stack traces or secrets are returned to the phone.
