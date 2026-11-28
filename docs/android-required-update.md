# Required Android updates

Version 1.0.13 / code 15 introduced an app-wide update gate before onboarding and authentication. Checks run on foreground entry and every five minutes while active. A higher server versionCode blocks app use; equal or newer builds pass. Connection errors and a 12-second timeout show Retry. Returning from an update rechecks. The check overlay keeps existing forms mounted.

The current candidate, 1.0.17 / code 19, uses Google Play updates only. Public GET /android-version returns latest_version_code, latest_version_name and the fixed Play listing URL with Cache-Control: no-store. Legacy channel query parameters are ignored. APK delivery and the /android-update.apk route have been removed.

ANDROID_LATEST_VERSION_CODE and ANDROID_LATEST_VERSION_NAME define the required Play release. Raise them only after that release is available to the intended Play audience. The app requests an immediate in-app update, resumes an interrupted update on foreground entry, and provides a Play listing fallback when Play cannot offer the flow. Cancellation or failure leaves the required-version gate in place.

A debug APK has a different signing certificate from the Google Play build. Test in-app updates using a Play-installed build and an eligible account. Local assembly and unit tests do not prove Play delivery, signing compatibility, track eligibility, or a completed device update. This feature cannot retroactively add a gate to old installations that never contained the update code.

The earlier code-14-to-15 direct APK device check is historical evidence for the removed delivery path. It is not acceptance evidence for this Play update candidate. Do not raise the live version requirement based on local build success.

Reference: https://developer.android.com/guide/playcore/in-app-updates/kotlin-java

## Play track acceptance still required

1. Install the lower version from the intended Google Play track with an eligible tester account.
2. Make a higher version available to that same account before raising the required server version.
3. Confirm the gate opens the immediate Play update and the updated app keeps its account and data.
4. Interrupt the update, return to Launch Circle, and confirm the Play update resumes.
5. Cancel or decline; confirm the app explains the update requirement and offers retry and the Play listing.
6. Verify equal/newer versions pass and a failed policy request shows Retry.

## Local validation — 2026-10-28

Android assembleDebug and testDebugUnitTest pass: 37 unit tests, zero failures. The existing version comparison test was updated for the Play-only policy model. Interrupted-update foreground handling and a false return from Play's startUpdateFlowForResult are now handled. Play-installed device acceptance remains open; no live required-version setting was raised during this work.

Backend: both update-policy tests pass. Full suite: 129 passed, 3 failed. All three failures reproduce against unchanged HEAD 15c0a09 in a separate temporary source extraction using the same dependencies. They attempt multiple apps for a non-admin owner and receive the existing one-app-per-person HTTP 409: test_payments.py::test_managed_price_uses_credit_sku_and_redeems_once; test_phase1.py::test_phase1_accelerated_acceptance_report_and_evidence_only_draft; test_recovery.py::test_replacement_respects_daily_limit_and_no_candidate_is_truthfully_at_risk. These remain a separate test/policy reconciliation task. Dependency snapshot: /home/cliu/.cache/launch-circle-validation-dependencies-20261028.txt.
