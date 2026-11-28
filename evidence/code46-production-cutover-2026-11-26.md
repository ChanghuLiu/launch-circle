# Launch Circle 1.0.44/code46 production release and API cutover

Date: 2026-11-26 (UTC). Scope: authorized code46 Production release verification, backup validation, production SQLite 0019→0021 migration, and API service switch. No Google Play copy was edited; release notes stayed blank.

## Play and target device

- Signed-in Play Console Production track for `com.launchcircle.testers` shows **Active**, latest release **46 (1.0.44)**, 178 countries/regions and 15 installs. This is an active Production release, not a draft/review state.
- ID12 / TCL T434J / serial `Z9UGHA7PHUTKA6XS` package-manager readback: `versionName=1.0.44`, `versionCode=46`, `installerPackageName=com.android.vending`, `lastUpdateTime=2026-11-26 11:01:12`. This confirms the installed official package is Play-delivered code46. No app/data was removed.
- Approved AAB remains `/home/cliu/Development/release-artifacts/launch-circle-1.0.44-code46-api-capabilities-r2-2026-11-24.aab`, SHA-256 `6d23d96b450812ea40f75577666d49881fc112ee596231c37a2a8e90e3f69db5`; no rebuild or upload occurred in this cutover.

## Backup evidence

- The first automatic post-install timer run was observed in systemd journal at `2026-11-26 03:21:27 UTC`; service `Result=success`, `ExecMainStatus=0`. It reported `recognized=14 keep=14 delete=0` and created `/var/backups/launch-circle/launch_circle-20261126T032127.888577Z.db`. The file was mode `0600`, 3,579,904 bytes, SHA-256 `d8388c7a2e17c180ac3a345201dedde9b74461a5e533585a2cf6a12653069026`.
- Isolated restore copy of that automatic snapshot: `PRAGMA integrity_check=ok`, zero foreign-key violations, Alembic `0019_user_activity_events`.
- The timer was still active/enabled after this run. At final readback the next trigger was `2026-11-27 03:19:35 UTC`.
- A fresh consistent pre-migration snapshot was made after stopping the API for the maintenance window. Service run `2026-11-26 16:23:18–16:23:19 UTC` exited 0 and created `/var/backups/launch-circle/launch_circle-20261126T162318.945584Z.db`, mode `0600`, 3,579,904 bytes, SHA-256 `1ff864d6c50bc6c7266e35eec82dfb077b5e6a5c64159977d30184ed35257ea7`. Isolated restore check passed: integrity `ok`, foreign-key violations 0, Alembic `0019_user_activity_events`; aggregates matched the live database immediately before migration.
- The cleaner reported 15 recognized backups and would delete exactly `backend.20260825T143119Z/data/launch_circle.db`. It then completed successfully; that one oldest recognized backup was removed by the approved `--keep 14` policy. No sidecar existed at that target. The containing directory and all other backups were left in place. A subsequent dry-run reported 14 recognized, 14 kept, 0 deletions. Existing `0644` backup files were not chmodded; the separately scoped permission remediation remains unperformed.

## API source and migration

- Staged immutable runtime archive: `/home/cliu/Development/release-artifacts/launch-circle-api-code46-2026-11-26.tar.gz`, SHA-256 `06e8623b0481b591b2754096d061994e3f68db866ae25b90a34bbdfa472ad888`; remote archive SHA matched. Extracted release path: `/home/ubuntu/launch-circle/releases/LC-CODE46-API-20261126/launch-circle-api`.
- The code46 source-hash manifest contains 116 paths. 114 matched the recorded hashes; two later backup-only paths differed (`app/services/sqlite_backup.py` and `deploy/launch-circle-backup.service`) because the standalone retention cleaner was subsequently updated. Neither is imported by the API runtime. The deployment archive contains 80 hash-verified `app/` and `alembic/` runtime/migration/config files; it excludes the backup utility, backup unit and test tree. Every included path matched its manifest hash; release/deployment files were not copied from the general dirty worktree wholesale.
- Before production migration, the exact staged migration code and production Python venv upgraded an isolated copy of the fresh production backup from 0019 to 0021. It preserved counts: users 42, apps 20, app groups 2, app-group app links 13, members 4, tester assignments 118; new queue rows 0. All 20 existing Apps became `PENDING_ATTESTATION`; no owner consent was fabricated. Integrity, foreign keys, both queue indexes, and four expected SQLite guards passed.
- Production API was stopped at `16:23:11 UTC`; Alembic ran `0019_user_activity_events → 0020_app_group_status → 0021_group_task_queue` from the staged release at approximately `16:24 UTC`. The systemd drop-in `zzzzzzzzzzzz-20261126-code46.conf` now points WorkingDirectory to the new immutable release. `systemd-analyze verify` passed, and systemd readback confirmed the new directory. API was active again at `16:25:17 UTC`.
- Production post-migration read-only checks: Alembic `0021_group_task_queue`; integrity `ok`; foreign-key check returned no rows; row counts remained 42/20/2/13/4/118; queue count 0; owner status count `PENDING_ATTESTATION=20`; indexes `ix_app_group_task_queue_group_status` and `ix_app_group_task_queue_user_status`; triggers `trg_no_assignment_without_owner_attestation`, `trg_no_group_join_without_owner_attestation`, `trg_no_new_assignment_for_closed_app_group`, `trg_two_new_assignments_per_user_day`.

## Post-cutover acceptance

- Public `/health`: HTTP 200, request ID `9b394fd3-eb96-4ad8-bead-9c5a95be5119`, body `{"status":"ok"}`.
- Public `/capabilities`: HTTP 200, request ID `613c6458-df47-40ac-97f7-f4445653faf9`, response `migration_revision=0021_group_task_queue`, `owner_attestation=true`, `app_group_selection=true`.
- Read-only old-client bootstrap checks: `/android-version` HTTP 200 (`9a560a2a-4606-4a18-a23a-8e6cce8a74bb`), `/pilot-config` HTTP 200 (`2fcba866-f0fd-4de4-b756-781c9a33a2ce`). OpenAPI readback still exposes `/v1/me`, `/apps`, `/app-groups`, owner-attestation and selected-group join routes (`a01eeb51-3315-4013-982f-fe7e07c33ad1`).
- Actual authenticated old-client user workflow and an owner’s App Group join were not exercised against production: no production test user/App action was authorized, and `GET /test-assignments/today` may dispatch tasks. No customer task, membership, attestation, or App data was created by acceptance. Therefore backend capability/route checks PASS; an authenticated production UI end-to-end flow remains unverified. Isolated Run10 PASS and Run13’s actual 0019 compatibility evidence remain unchanged; Run10’s old-API capability-off case used a simulated response, and Run13 had no App to show an owner-attestation card.
- Play listing and release text remain unchanged. The previously canceled 15/15-delivery and 14-day notice gates remain waived; actual notice records remain as previously documented (15 sent, one with receipt evidence).

## Rollback

- If the new API fails, keep the live SQLite database at 0021 and switch the service WorkingDirectory back to `/home/ubuntu/launch-circle/releases/LC-ADMIN-LOGS-20261123-r2/launch-circle-api`; reload systemd and restart the API. Do not downgrade Alembic or overwrite the live database from either backup. The code46 client fails closed if it sees old API without `/capabilities`; queued work pauses until the compatible API returns.
- The API remained healthy after cutover; no rollback was invoked.

## Read-only post-cutover follow-up — 2026-11-26 ~16:34 UTC

No specific production account/App/Group write test was designated and authorized in the current records. A read-only aggregate check found 20 Apps pending attestation, 2 open groups, 4 current group members, zero post-cutover membership/owner-join success events, zero queue rows, zero assignments created after cutover, and zero activity failures/HTTP error events. Five API requests appeared in the post-cutover service journal; none returned 4xx/5xx and no error/exception lines were found. No production business data was modified. Full aggregate evidence and authorization scope: `code46-post-cutover-readonly-followup-2026-11-26.md`.
