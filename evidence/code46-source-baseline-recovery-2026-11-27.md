# Launch Circle code46 source baseline recovery — 2026-11-27

## Result

A dedicated worktree was reconstructed from the retained code46 release-candidate source inputs and frozen source-hash manifest. All 105 Android source/build-input entries match the manifest exactly (SHA-256 per file). The manifest is tied by the contemporaneous release candidate record to the approved production AAB for `com.launchcircle.testers` 1.0.44/code46. The deployed production API source is also restored from its immutable code46 archive and checked against the API source-hash manifest.

This is a **manifest-verified reconstructed source baseline**, not a claim that the reconstructed source independently reproduces the signed AAB byte-for-byte. The signed production AAB remains the immutable reference artifact.

## Production artifact reference

- AAB: `/home/cliu/Development/release-artifacts/launch-circle-1.0.44-code46-api-capabilities-r2-2026-11-24.aab`
- SHA-256: `6d23d96b450812ea40f75577666d49881fc112ee596231c37a2a8e90e3f69db5`
- Package/version: `com.launchcircle.testers`, `1.0.44` / code `46`
- Source manifest: `evidence/launch-circle-release-candidate-source-hashes-1.0.44-46-2026-11-24.txt` (105 entries)
- Release record: `docs/RELEASE_CANDIDATE_1.0.44_46_2026-11-24.md`

## Production API reference

- Archive: `/home/cliu/Development/release-artifacts/launch-circle-api-code46-2026-11-26.tar.gz`
- SHA-256: `06e8623b0481b591b2754096d061994e3f68db866ae25b90a34bbdfa472ad888`
- The archive contains 80 runtime/migration/config files. All 80 paths are present in `evidence/launch-circle-api-release-candidate-source-hashes-1.0.44-46-2026-11-24.txt` and match their frozen hashes. Of 116 paths in the broader API source manifest, 113 currently match; the three exceptions are `launch-circle-api/app/services/sqlite_backup.py`, `launch-circle-api/deploy/launch-circle-backup.service`, and `launch-circle-api/tests/test_admin.py`. The first two are later backup-retention changes; the third is a later test-tree revision and is not included in the deployed runtime archive. The production cutover record documents which 80 files were deployed.

## Reconstruction and verification

- Local/remote refs, tags, worktrees, reflogs, stash and unreachable Git objects were inspected. No code46 commit, tag, stash or complete alternate source checkout was found; latest available committed Android baseline was code20.
- The five initial capability-repair edits, plus the `ApiCapabilities.kt` and repository HTTP-status changes, were reversed only in temporary reconstruction files using the recorded Codex patch history. The resulting seven files were accepted only after matching their frozen manifest hashes.
- The remaining manifest paths were copied from the retained release-candidate source tree into the independent `recovery/launch-circle-code46-baseline-20261127` worktree. Final result: **105/105 SHA-256 matches**.
- The isolated worktree began at Git commit `1933ff38e2e5ba532a035561b326b91a3c533fd8` (tracked Android version code20). No files in the original shared-pool worktree were staged, reset, cleaned, or overwritten.
- The original worktree still contains its existing user changes; this recovery did not use `git add -A`.

## Limits and next check

The Android manifest verifies all 105 listed client inputs. The API deployment archive independently verifies all 80 production runtime/migration/config inputs; the broader API manifest has the three exceptions listed above. These checks do not establish byte-for-byte AAB reproducibility or recover a historical Git commit that never existed. Do not publish this baseline as a new production release.
