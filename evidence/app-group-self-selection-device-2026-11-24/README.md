# ID12 App Group self-selection acceptance — 2026-11-24

## Preview isolation and device

- Device: ID12, T434J / Android 16 (device serial recorded in local test session only).
- Installed preview: `com.launchcircle.testers.groupselftest`, version `1.0.42-group-selftest (44)`, local debug signature. APK: `/tmp/lc-id12-group-selftest-20261124/android/app/build/outputs/apk/debug/app-debug.apk`; SHA-256 `fda58b47b5115d0d9e0af294af46986ee6c786689e6cb9d48246ba90dd9e1655`.
- Generated BuildConfig confirms API `http://127.0.0.1:18000/`, `USE_DEMO_REPOSITORY=false`, and development authentication enabled. API ran in a disposable Python 3.12 Docker container backed by `/tmp/lc-id12-group-selftest-20261124/data/preview.db`; the phone reached it only through `adb reverse` to localhost. The seeded accounts and Apps were synthetic. No Google sign-in or production endpoint was used.
- Before install, ID12 had the official `com.launchcircle.testers` 1.0.42 (44) and an existing `com.launchcircle.testers.uipreview`. Both remained installed after preview install; official-package `firstInstallTime` and `lastUpdateTime` remained 2026-11-19 and 2026-11-20 respectively. No official-app data was cleared or changed.

## Scenario results

- Seeded independent Daycare and USB user/App pairs with an already-saved, ready `Pegs and Jokers` record. Each account opened **My Launch → Browse App Groups**; neither used Add App or re-entered App details.
- Initial cards showed Daycare: 12 mapped exempt Apps, **0 requiring tests**, 3 open App slots, 2 mutual-testing members. USB showed 1 required App, 14 open slots, 1 member. Choosing Daycare added only the Daycare synthetic user's App and membership there. The updated card showed 12 exempt + 1 required App, 2 slots left and 3 members.
- Choosing USB with the other synthetic account added only that account's App and membership to USB. After the selection the card showed 2 required Apps, 13 slots left and 2 members. No automatic group switch occurred.
- After both joins, each chooser showed **0 / 12 qualified testers**, **not started**, day **0 / 14**; each My Launch dashboard showed **0 / 12 ready** and “Waiting for tester activity.” Database readback confirmed `testing_start_at=NULL` and `WAITING_FOR_TESTERS` for both Apps.
- Task synchronization remained scoped to the selected group: Daycare Pegs and Jokers produced 2 peer tasks; USB Pegs and Jokers produced 1 peer task and the USB user received 1 other-App task. Both Apps had 0 self-assignments. All 4 resulting tasks were confined to the synthetic database.
- Unchecked consent: on ID12, pressing “Confirm and join” while the checkbox was clear left the dialog open and did not submit. A direct isolated API request returned **422 `APP_GROUP_CONSENT_REQUIRED`**; App mapping, owner membership and task count were unchanged.
- Duplicate: resubmitting Daycare join returned HTTP 200 with `already_joined=true`; assignment count stayed 2 before and after. In the UI, an already-joined App showed a disabled “已入组” control.
- Full/closed: the disposable fixture was then adjusted to 15 Daycare Apps (14 exempt + 1 required) and a closed USB group. ID12 showed **小组已满** / **小组已关闭** and disabled selection. Direct API attempts returned **409 `APP_GROUP_FULL`** and **409 `APP_GROUP_CLOSED`**; the blocked App remained unmapped, its owner remained unjoined, and assignment count did not change.

## Evidence images

All screenshots are from synthetic accounts and contain no production account or customer data.

| Screenshot | SHA-256 |
|---|---|
| `daycare-options.png` | `e6b7b1dbd1ed9eef27a063fafe5bd63c800280298c843eb97517cbd2a047ee92` |
| `daycare-joined-progress.png` | `a97ad497fc0af6b6e323d5ab9110ab6a004a24d78a3e8286a70a028cc11d0df5` |
| `daycare-my-launch-progress.png` | `a44c68d4803a088464a6453227b779f20a0a4a3fbdeca6092be9ebe925a9efce` |
| `usb-joined-progress.png` | `815cf007b76fad0d4da6a9a40179e47f2f4734d011fffda644c4601e849672fe` |
| `usb-my-launch-progress.png` | `ff65185d3d9c9fa70c2807633ca2e5fddcd7f99db11f5e4c5b3ecb6f8a5dd512` |
| `full-closed-options.png` | `7a6c5ecce5a1058d5c0b291ebcbdc94a25e2708d794912eff702e7731b9cc9a2` |

## Verification

- Isolated backend full suite: **169 passed, 0 failed**, 9 existing warnings; `pip check` and focused Ruff passed. A host-side pytest invocation initially lacked `fastapi`; the full suite was rerun successfully in the Python 3.12 container.
- Android preview `:app:assembleDebug` succeeded; Android `:app:testDebugUnitTest`: **38 passed, 0 failed, 0 errors, 0 skipped**.
- No production database/API, production group, recruitment, or task was touched. No Play package was replaced or released.
