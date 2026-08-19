# Launch Circle Android

Kotlin and Jetpack Compose client for **Launch Circle: 12 Testers**.

## Implemented

- Material 3 first-run onboarding and Google sign-in
- debug-only local development authentication
- My Launches, guided Add App, Launch Dashboard, and Tester Status
- automatic tester matching and Phase 1 lifecycle presentation
- Today Tests, mission flow, and factual feedback submission
- invite creation, share, direct invite-code acceptance, and join confirmation
- Launch Circle Google Group onboarding
- real Retrofit and in-memory demo repositories

## Backend modes

Local emulator:

```text
launchCircleApiBaseUrl=http://10.0.2.2:8000/
launchCircleUseDemoRepository=false
launchCircleEnableDevelopmentAuth=true
```

Physical phone on the LAN uses `http://HOST_LAN_IP:8000/`.

External pilot uses an HTTPS URL, the real repository, and disabled development auth. Release builds force both demo data and development authentication off.

## Google authentication

Provide the Google OAuth Web client ID used by the backend:

```text
googleServerClientId=YOUR_WEB_CLIENT_ID.apps.googleusercontent.com
```

Do not place OAuth client secrets, keystores, or signing credentials in the project.

## Build

```bash
./gradlew testDebugUnitTest
./gradlew assembleDebug
```

See `ACCEPTANCE.md` for isolated local acceptance and `../PILOT_DEPLOYMENT.md` for the external HTTPS pilot build configuration.
