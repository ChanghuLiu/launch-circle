# Acceptance record — 2026-10-21

## Automated verification

- Backend: 85 tests passed, zero failures. Includes idempotent replays, altered-payload rejection, access isolation, source/build validation, incomplete pass rejection, linked fix/retest behavior, flag-off behavior, report access and enrollment continuity.
- Capacity scenario: 12 synthetic participants across 3 apps; daily assignment duplication does not create new people or restart ongoing continuity; leaving one app does not alter the other apps. This is a data-model test, not recruitment proof.
- Android: 31 unit tests passed; debug APK assembly and lintDebug succeeded.
- Ruff checks passed for the new backend evidence modules, scripts and tests.
- Migration: empty database upgrade to 0015 succeeded. Upgrade/downgrade/re-upgrade retained a pre-existing synthetic user.
- Git whitespace check passed.

Existing phase0.py lint debt: 122 B008 dependency-default warnings, identical to baseline; no broad lint cleanup was included.

Existing test warnings: Starlette/httpx deprecation and SQLAlchemy model class names considered for pytest collection.

## Real device observations

Samsung SM_J327W, Android API 27, Notes Escape package com.notesescape.sdocx, installed version code 14:

1. Main screen displayed the file-selection action.
2. Opening file selection displayed Android Documents UI.
3. Returning without selecting a file restored Notes Escape, with no selected files and the selection action still available.

One CODEX_ASSISTED PASS was accepted for this narrow navigation mission. Replaying the saved request returned the same run ID. Summary recorded one run and one reported device, zero manual participants and no confirmed Google eligibility. No conversion/export, full Notes Escape regression, or Play enrollment was tested.

The parallel Launch Circle debug app was installed without removing or clearing the normal app. Guided assignment UI was observed using explicitly synthetic development sessions. That inspection found a legacy daily-todo status mismatch; an independent assignment-state endpoint and client query fixed it. The original phone disconnected before final UI verification. Follow-up verification on TCL K12 (T434J, Android API 36) completed that check: the final parallel APK installed successfully, the synthetic active assignment displayed mission days without a repeated opt-in confirmation, and the Day 1 form displayed candidate version 14. Untouched steps remained NOT_RUN and the actual Save button node was disabled. No HUMAN_MANUAL evidence was submitted during this assisted UI inspection.

The initial black screenshot did not count as UI coverage. The reconnected TCL K12 subsequently produced readable UI hierarchies and the explicit follow-up checks above. That check initially added Launch Circle UI coverage. The separate actual K12 Notes Escape navigation check below subsequently added device-specific workflow evidence.

## Reports and handoff

The refreshed owner session successfully exported private JSON and Markdown containing the one observed run. Credentials, session files, device request envelopes and customer-free internal reports remain outside Git.

Production feature flag remains default-off. No release upload or production deployment was performed.

## K12 evidence round trip follow-up

On the connected TCL K12 (T434J, API 36), Notes Escape version code 14 displayed its main screen and selection controls. Tapping Select .sdocx files opened com.google.android.go.documentsui. Android Back returned to Notes Escape with No .sdocx files selected and the selection action still present. No blocker was observed within this narrow navigation scope. No conversion or export operation was exercised.

The adapter read installed version/device facts and submitted these actual observations as CODEX_ASSISTED. Exact saved-request replay returned the same run ID, 5fde1ade-bc6c-4809-a5bf-8cb4af548071. The owner report then exported successfully with two total runs and two reported devices, both assisted. Manual participant count and reported joined participant count remained zero; Google eligibility remained unconfirmed. No human test result was entered through the UI.

This closes the connected-device evidence submission/replay/export check. Recruitment, Google enrollment verification and a real customer testing campaign remain outstanding.

## Publisher evidence UI follow-up

The gated My Launch → Testing evidence screen was added for app owners. It separates participant observations, candidate-build device/results and all-build execution sources, includes refresh and candidate version selection, and lists failure/retest states with one-time fix declaration controls. Backend authorization and fix/retest validation remain unchanged.

TCL K12 displayed the expected pilot data: assigned participants 1 (synthetic), joined participants 0, owner-confirmed joined 0, continuous 14 days 0, manual reporting participants 0, candidate-build devices 2 and assisted runs 2. The UI displayed no recorded failures. Saving candidate version 14 succeeded with an HTTP 200 response and a visible Candidate version saved notice. The candidate form asks only for version code; fix descriptions are collected only for fix declarations, where the backend persists them.

Android unit tests (31), final debug assembly and lintDebug were rerun successfully. Failure-card submission was not exercised against fabricated device failures on the phone; existing backend tests cover owner isolation and linked fix/retest validation. This remains an internal English pilot, default-off and undeployed.
