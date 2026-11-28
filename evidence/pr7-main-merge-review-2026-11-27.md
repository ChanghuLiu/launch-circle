# PR #7 main sync and code46 baseline review — 2026-11-27

## Ref and change-set snapshot

- Existing Draft PR: [#7](https://github.com/ChanghuLiu/launch-circle/pull/7), base `main`, head `fix/launch-circle-capabilities-code47-20261127`; no new PR was created.
- Before sync: PR head `de2f2853f43da2dac880b90e48c65d259a803b1f`; `main` was eight commits ahead and the PR branch 48 commits ahead. The three-dot tree diff was 216 files (21,589 insertions / 854 deletions).
- Sync work is isolated in `/home/cliu/mobile/worktrees/launch-circle-pr7-merge-20261127`; the original code46 candidate worktree and the pre-existing shared-pool worktree were not used for merge resolution.

## The eight commits on main

1. `c6f29cf` updates Play listing copy to describe genuine peer QA without promising test participation or production approval. Kept.
2. `7df2993` gates app-specific Play opt-in behind shared tester-group membership, then a separate app opt-in. Kept in behavior: the candidate's `TesterGroupAccessCard` saves group access for the same Play email; `EvidenceAssignmentScreen` withholds the per-app Play link until shared access is ready, separately gates any app-specific group confirmation, and only enables opt-in confirmation after opening that app's link. The Today copy now states the shared-group-once / per-app-opt-in rule. This is stronger state-based gating than the main-only screen's local checkbox.
3. `e62889e`, `e9efc4b`, `405d1e1`, `d1b744b`, `31b1fe2`, and `a741bfb` refine the account-deletion/privacy page identity, contact and retention copy. Kept as main's versions; these HTML files are not overwritten by code47 changes.

The only content conflict was `launch-circle-android/.../PilotLaunchScreens.kt`. Resolution retained the reconstructed code46/code47 implementation, including the state-gated assignment screen, and carried over main's user-facing opt-in rule. The six policy/listing commits merged without conflicts.

## File classification before merge

The 216-file PR diff grouped by repository path:

- 63 Android application source/resource files: historical Launch Circle functionality needed to bring the old main baseline forward to the reconstructed production client, plus the small capabilities repair.
- 8 Android build/release metadata files.
- 69 API source, migration and deployment files: historical production functionality and the recovered code46 API snapshot, plus narrowly scoped CI alignment.
- 44 test files.
- 13 evidence files and 17 documentation/release files, including the code46 manifests, recovery explanation and code47 release/CI records.
- 2 repository workflow/listing files.

These are not all code47 changes. The historical production features, release reconstruction, tests/evidence, and code47 fix have distinct commits and records. No unrelated product tree was found in the diff. The main-only privacy/listing changes become part of the shared base after the merge.

## code46 source and API manifest exceptions

- No historical code46 commit or tag was found. The baseline remains a manifest-verified reconstruction, not a claim of exact historical Git identity or byte-identical AAB reproduction.
- The 105-entry Android manifest matches 105/105 reconstructed Android inputs.
- The 80-file deployed API archive (`launch-circle-api-code46-2026-11-26.tar.gz`, SHA-256 `06e8623b0481b591b2754096d061994e3f68db866ae25b90a34bbdfa472ad888`) matches 80/80 files in the restored API commit `ed5eb0ba16993f9265bce7d0492fde151f373de0`.
- At that restored API commit the broader 116-entry source manifest matches 113/116. The verified exceptions are:
  - `app/services/sqlite_backup.py`: expected `c435c012db0dbc2db04da3ceb0b0cbf151989ba3349ce23c9905aebafdd1911e`; restored commit `2ebd57cc970a8a24b3c675a5923b2ecbcea78bcb012baae02c9f8eb5e3df494c`.
  - `deploy/launch-circle-backup.service`: expected `f2460d6e9152de59d8520ce6956beee4c8a739ad9b15d3a56bce9be99ea945f7`; restored commit `3d0f4ca163a8f082fdba526a3365095e98054962dffa60f4b823127fb1a8ca1f`.
  - `tests/test_admin.py`: expected `3820b9468a04faaf98fcb0d1f4d47c705ba671e032ae9e2c2cde23581ced633e`; restored commit `21ec70fdea08941a19749f77789d1af006f148fcd48f5d9108df90af72118dee`.
- None of these three paths is in the 80-file production deployment archive. Their recorded manifest-vs-source discrepancies therefore do not change the verified production runtime. Later CI work changed the backup helper to set mode `0600` and updated admin test request fixtures; it did not run a production backup. The service unit remains the recovered source version. The frozen expected variants were not found in reachable Git file history or current local worktree copies, so their exact originating revision is unverified.

## Device and automated UI evidence

- ADB found no physical ID1–ID11. It found two emulators: `emulator-5554` (Android 17 / API 37, Play Store image) and `emulator-5556` (existing `ParentCheckIn_API27` / API 27 image). No ID12 action was attempted.
- The standalone evidencepilot code47 APK installed on `emulator-5554`; it cold-started to onboarding and then `Continue with Google`. No account was selected and no credentials were entered. Authenticated Home/My Launch/Add App/App Groups and live network/lifecycle scenarios therefore remain unverified until the user signs in on `emulator-5554`.
- Compose instrumentation tests initially compiled but all three failed at interaction time on API 37 because the bundled Espresso event injector reflects `InputManager.getInstance`, absent on that emulator. This is a test-harness/API compatibility issue, not an app crash.
- The same three instrumentation tests passed on the existing API 27 emulator (`ParentCheckIn_API27`): shared-group gate, per-app opt-in-link/confirmation gate, and app-specific group gate; **3 passed, 0 failed**. This is emulator evidence, not real-device evidence. No user app was uninstalled and no physical Play installation was changed.

## Remaining checks

- GitHub Actions run [46085441896](https://github.com/ChanghuLiu/launch-circle/actions/runs/46085441896) completed successfully on merge commit `296439e7450e32a10049b4abfc203672976bad05`: Android tests/debug build/lint and Backend Python 3.12/3.14 tests, lint and empty-database Alembic migration passed.
- Rebuilt the signed code47 AAB after CI from that exact source commit. Final artifact SHA-256 is `1f46ef207455447577c6bde21f2661baf941dcbba4249da2b6a45137e8fabde4`; `jarsigner -verify` reports verified and its certificate SHA-256 matches code46. Detailed release record: `launch-circle-android/releases/code-47-2026-11-27.md`.
- PR #7 is still Draft. No Play upload, review submission or rollout occurred. Do not merge/publish until authenticated UI acceptance and the physical-device gate are resolved.
- The user must complete Google sign-in in the `Continue with Google` flow on `emulator-5554`; after that, resume the authenticated emulator page, network and lifecycle checks. No ID12 retry is planned. Current screenshot: `evidence/pr7-emulator-code47-2026-11-27/02-login-current.png`.
