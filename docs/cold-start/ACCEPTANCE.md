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

The initial black screenshot did not count as UI coverage. The reconnected TCL K12 subsequently produced readable UI hierarchies and the explicit follow-up checks above. This adds Launch Circle UI coverage; it does not extend the earlier Notes Escape workflow result to another device.

## Reports and handoff

The refreshed owner session successfully exported private JSON and Markdown containing the one observed run. Credentials, session files, device request envelopes and customer-free internal reports remain outside Git.

Production feature flag remains default-off. No release upload or production deployment was performed.
