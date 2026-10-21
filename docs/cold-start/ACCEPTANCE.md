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

The parallel Launch Circle debug app was installed without removing or clearing the normal app. Guided assignment UI was observed using explicitly synthetic development sessions. That inspection found a legacy daily-todo status mismatch; an independent assignment-state endpoint and client query fixed it. The final APK was rebuilt and tested, but final device UI verification of that fix remains pending because the original phone disconnected. No fabricated final UI pass is claimed.

A second device's black screenshot did not count as UI coverage. Later-connected phones were not treated as substitutes for the completed device observations.

## Reports and handoff

The refreshed owner session successfully exported private JSON and Markdown containing the one observed run. Credentials, session files, device request envelopes and customer-free internal reports remain outside Git.

Production feature flag remains default-off. No release upload or production deployment was performed.
