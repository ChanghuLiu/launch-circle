# Owner-selected App Group UI and progress — isolated acceptance — 2026-11-24

## Implemented locally

- Group choice data now includes remaining App slots, number of mapped Apps that require testing, exempt App count, and active mutual-testing member count. Counts are based on `AppGroupApp` and each App's `no_test_required` flag.
- Group app cards mark each visible App as `免测 App` or `需测试`; exempt Apps remain distinguishable and are skipped by `sync_group`.
- After an App is mapped to a group, the owner selection screen shows that App's lifecycle-qualified tester count, start timestamp, status and day. This is served from a read-only progress calculation using the production `active_qualifying` and `timeline_values` helpers; the route does not call recovery or lifecycle mutation functions. Null start time renders as not started/day 0. Joining and slot capacity do not set `testing_start_at`.
- The server still requires explicit consent, verifies ownership/setup/group state/capacity in the join transaction, and uses existing group-scope authorization, deduplication, quotas and own-App exclusion.

## Isolated scenario and tests

`tests/test_owner_app_group_selection.py` now creates the requested fixture: Daycare has 12 mapped Apps with `no_test_required=true`; USB has one mapped test-required App; Josh has a saved/configured Pegs and Jokers App with no group link. The parameterized case submits both choices and confirms the App and owner membership point only to the selected group, the displayed group metrics are correct, exempt Apps are individually marked, and the App remains `WAITING_FOR_TESTERS` with no start timestamp/day 0.

Additional covered cases confirm:

- Joining the fifteenth App slot succeeds but does not start the cycle or change the App out of `WAITING_FOR_TESTERS`.
- Repeated submission is idempotent and creates no extra assignments.
- Missing consent creates no group link, membership, listing or tasks.
- Full and closed groups return their existing conflict codes without partial writes.
- Two owners competing for one remaining slot yield one winner, with the group capped at 15 Apps.
- Reciprocal assignment sync retains owner exclusion and task de-duplication; new assignments do not count as qualified until the opt-in/install and lifecycle conditions are met.
- A legacy App already mapped to a group but missing its owner's membership remains selectable only in that same group; explicit consent adds the owner membership without moving the App or starting its timer.

## Verification

- API isolated copy, Docker Python **3.12.16**: full backend suite **169 passed, 0 failed, 9 warnings**. `pip check` passed. Focused Ruff on `app/api/pool.py` and `tests/test_owner_app_group_selection.py` passed.
- Android: `:app:testDebugUnitTest` **38 passed, 0 failed**; `:app:assembleDebug` succeeded. Debug APK SHA-256: `b7bd97595e080dfc61840a868cb598b655606d6cdc14c45fd53dc4f2907ba657`.
- `git diff --check` passed. No Android emulator is configured, so UI acceptance is based on API integration coverage, Kotlin compilation, unit tests, and APK assembly; no Android device was installed or operated.

## Scope

Changes are in the existing local worktree on `codex/launch-circle-admin-20261026`; pre-existing dirty and untracked files were preserved. No commit, production database operation, deployment, migration, recruitment change, App move, or task dispatch occurred.
