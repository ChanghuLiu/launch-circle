# Acceptance record — 2026-10-21

Status: technical pilot complete for review. The new functionality remains default-off outside the isolated development pilot. No real customer cohort or 14-day customer campaign was completed.

## Final automated verification

- Backend: 88 tests passed, zero failures. Coverage includes idempotent replay/conflicts, actor/tenant/source/build restrictions, incomplete pass rejection, owner report access, enrollment continuity, scoped run details, exact original-step retests, and delayed retests of missed missions without rewriting their history.
- A 12-synthetic-participant × 3-app scenario verifies independent enrollment and no duplicate person counts across daily assignments. This is a data-model test, not recruitment proof.
- Android: 32 unit tests passed; final debug APK assembly and lintDebug succeeded. Report formatting retains original observations, sources, synthetic labels, retest linkage and unconfirmed Google eligibility.
- Ruff checks for new backend modules/scripts/tests and Git whitespace checks passed.
- Additive migration 0015: empty database upgrade and downgrade/re-upgrade with an existing synthetic user retained that user's data.
- Existing phase0.py lint debt remains 122 B008 warnings, identical to baseline. Existing test warnings concern Starlette/httpx deprecation and SQLAlchemy class names considered for pytest collection.

## Actual bounded Notes Escape device observations

Package com.notesescape.sdocx, installed version code 14:

| Device | API | Actual observed scope |
| --- | --- | --- |
| Samsung SM_J327W | 27 | Main screen → Android document picker → cancel/back → main screen with no file selected and selection action present |
| TCL K12 / T434J | 36 | Same bounded navigation using com.google.android.go.documentsui |

Each device produced one explicitly CODEX_ASSISTED run. Exact saved-request replay returned the original run ID. Notes Escape's final report remains two assisted runs across two reported devices, with zero manual participants, zero reported joined participants and unconfirmed Google eligibility. Conversion, export and full app regression were not exercised.

## Launch Circle UI on TCL K12

The optional com.launchcircle.testers.evidencepilot package installed without removing or clearing the normal app. Authentication used explicitly synthetic internal sessions; Google sign-in was not tested end to end.

- Guided active assignment displayed mission days without a repeated opt-in confirmation.
- Day 1 displayed the confirmed candidate build; untouched steps stayed NOT_RUN and the actual Save button node was disabled.
- Publisher counts matched API data: assigned synthetic participant 1, joined 0, manual reporting 0, two observed devices and two assisted runs in the Notes Escape pilot.
- Empty candidate version disabled saving. Selecting version 14 succeeded with a visible notice and a matching backend update.
- Final APK was reinstalled after the last changes and the original Notes Escape internal publisher/report controls were smoke checked again.

## Synthetic failure/fix/retest UI validation

A separate publisher, tester and app labeled SYNTHETIC UI FIXTURE - NOT CUSTOMER TESTING were created only in the isolated pilot database. The pre-seeded AUTOMATED_RUNNER failure is a deliberate fixture, not an actual app defect or customer complaint. It never contributes to the separate Notes Escape report.

On K12:

1. The owner declared a fixture fix using the installed pilot build (version code 10); the UI showed READY_FOR_RETEST.
2. View recorded steps displayed the original FAIL observations, explicit synthetic note/source and fix declaration.
3. The owner explicitly selected assisted recording, entered the three original fixture observations and saved a linked retest. It showed VERIFIED_FIXED only after the passing run existed.
4. The assigned synthetic tester opened Tests → Day 1 → Recorded runs and retests → original failure. Manual and assisted choices were shown only as permitted by that actor. The assisted option was selected; a second linked UI retest saved successfully without an owner-summary authorization error.
5. Final fixture report: three runs (one synthetic automated failure plus two assisted UI retests), zero manual participants, zero reported joined participants, state VERIFIED_FIXED. This validates software state transitions only; it proves no real defect repair or enrollment.

## Native report save/share

The owner prepared a report snapshot in the app. Android document storage saved JSON and readable text into Downloads under explicit ui-fixture filenames. Readback verified run details, sources, synthetic labels and unconfirmed Google eligibility. That snapshot contained the failure plus the first retest; the final owner API report was separately checked after the tester's additional run.

Share report opened com.android.intentresolver with an app-private report URI and temporary read access; the chooser was dismissed without choosing a recipient or sending a message. The FileProvider is not exported and exposes only the dedicated report-cache subdirectory.

Credentials, sessions and raw device/request evidence remain outside Git. Only labeled synthetic report exports used for the native save test were placed on the test phone.

## Remaining real-world work

CUSTOMER_PILOT_RUNBOOK.md defines the 2–3-app handoff. Actual campaign links/builds/workflows and consenting real participant identities have not been supplied. Recruitment, Google enrollment verification, a real continuous testing period and production rollout remain outstanding. Current circle capacity includes the owner and permits 14 other testers. The evidence UI is internal-pilot English; large-campaign pagination and performance remain future work.
