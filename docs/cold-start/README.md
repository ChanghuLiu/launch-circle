# Launch Circle cold-start technical pilot

For a publisher with only 2–3 existing customers, recruit a shared pool of real participants. Each participant independently joins each eligible app through its Google Play testing link. Devices and automated runs do not fill participant places.

## Scope

Feature-gated enrollment observations, guided mission evidence, candidate-build tracking, scoped failure/fix/retest records, device evidence ingestion, and owner report export. Existing mission days remain 1, 3, 5, 8, 11, 14. Runs do not automatically award legacy completion or reliability credit. This is a technical pilot, not a completed customer campaign.

## Enable locally

In launch-circle-api, install the project with development dependencies, run alembic upgrade head, and set COLD_START_EVIDENCE_ENABLED=true. The flag defaults to false. Migration 0015 adds four evidence tables without rewriting existing records.

For a disposable internal pilot, use APP_ENV=development and an absolute SQLite filename beginning launch-circle-evidence-pilot-. Run:
```sh
python -m scripts.seed_evidence_pilot --version-code 14 --session-file /private/path/session.json
```
Seed identities and assignment timestamps are synthetic; they prove neither Google enrollment nor real tester participation. Keep generated sessions outside Git.

Android pilot build (from launch-circle-android):
```sh
ANDROID_HOME=/home/cliu/Android/Sdk ./gradlew :app:testDebugUnitTest :app:assembleDebug :app:lintDebug -PlaunchCircleEvidencePilotBuild=true -PlaunchCircleApiBaseUrl=http://127.0.0.1:8786/
```
This optional build uses com.launchcircle.testers.evidencepilot, preserving the normal app and its data. Use adb reverse for a loopback server. minSdk remains 27.

## API

All evidence routes require authentication, the enabled feature flag, and matching assignment/app ownership. Unauthorized objects return 404.

| Route | Purpose |
| --- | --- |
| POST /assignments/{id}/enrollment-evidence | Append JOINED, LEFT or UNKNOWN observation; server timestamp |
| GET /assignments/{id}/evidence-status | Actual assignment state, distinct from daily todo display |
| POST /apps/{id}/evidence/build | Owner sets candidate version code |
| GET /missions/{id}/evidence-context | Assigned steps, package and candidate version |
| POST /missions/{id}/runs | Append validated, idempotent observations |
| GET /missions/{id}/runs | Read scoped history |
| GET /runs/{id}/detail | Scoped original observations, fix and retest context |
| POST /runs/{id}/fix | Owner declares target fix build |
| GET /apps/{id}/evidence-summary | Separate participant, build, device and source totals |
| GET /apps/{id}/evidence-report | Owner-scoped summary and run details |

HUMAN_MANUAL requires the assigned tester identity. CODEX_ASSISTED and AUTOMATED_RUNNER remain explicitly labeled. Idempotent retries must reuse the exact request and key. A fix declaration alone never verifies a fix: a linked passing retest on the declared build and matching steps is required.

## Publisher evidence screen

With the evidence flag enabled, open My Launch → Testing evidence. The owner can refresh participant observations separately from device/build results, inspect source totals and failing run states, set a positive candidate version code, and declare a target fix version with a description. Fix declarations remain unverified until a linked retest passes on that build. A declared fix is shown read-only after recording. Open View recorded steps → Retest recorded failure, explicitly select the recording source, repeat the original steps and save. Assigned testers can reach the same detail/retest flow from their mission → Recorded runs and retests. Owner-only summaries are not requested by tester submissions.

A partial original failure is retested against exactly its original step scope, rather than claiming full-mission coverage. Changing the candidate away from the fix build disables retest context until the versions agree. Backend package, actor, assignment, build, step and idempotency checks remain authoritative.

Prepare latest report creates an owner-scoped snapshot. Save report JSON or Save readable report opens Android document storage; Share report opens the chooser with a temporary read grant to the report file only. The chooser does not automatically send to a recipient. App-private sharing files are isolated under evidence-reports and old files are pruned when preparing another share. Refresh the report snapshot after new observations. CLI export remains available.

## Device evidence and exports

Run the mission externally first; the adapter does not execute arbitrary app workflows or generate observations. Save the real step instruction, expected behavior, actual observation and result in JSON. Set LAUNCH_CIRCLE_ACCESS_TOKEN privately in the environment; never pass tokens as command arguments.

```sh
python -m scripts.submit_device_evidence --help
python -m scripts.export_evidence_report --base-url http://127.0.0.1:8786 --app-id APP_ID --output-directory /private/path/export
```

The device adapter reads installed package/version and device facts through ADB. Offline/missing app produces a local blocked precheck, not an invented server pass. It saves a durable request; --retry replays it without re-reading the device. Export writes private JSON and Markdown with exclusive creation. Transport permits HTTPS or loopback HTTP and rejects credential-forwarding redirects.

## Customer pilot gate

Recruit and confirm actual participants, independently confirm Play opt-in for each app, set a candidate build, run assigned core workflows, triage failures, upload fixes and record retests. Use Play Console to assess applicable eligibility. The app's 14-day estimate uses recorded events, cannot backdate participation, and always reports google_eligibility_confirmed=false.

See BASELINE_AND_GAPS.md and ACCEPTANCE.md before rollout.

## Repeatable synthetic UI validation

The development-only scripts.seed_evidence_ui_fixture command creates a separate, clearly labeled synthetic publisher/tester/app with a pre-seeded failure. It is restricted to the isolated evidence-pilot SQLite database, loopback API, development mode and enabled flag. Its data is never real customer testing or a real observed defect. Use a fresh private --session-file path. Never run it against production or include its identities/results in a real campaign.

See CUSTOMER_PILOT_RUNBOOK.md for the real pilot handoff and remaining required inputs.
