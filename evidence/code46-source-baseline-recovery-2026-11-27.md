# Launch Circle code46 source baseline recovery — 2026-11-27

## Result

A dedicated worktree was reconstructed from the retained code46 release-candidate source inputs and frozen source-hash manifest. All 105 Android source/build-input entries match the manifest exactly (SHA-256 per file). The manifest is tied by the contemporaneous release candidate record to the approved production AAB for `com.launchcircle.testers` 1.0.44/code46.

This is a **manifest-verified reconstructed source baseline**, not a claim that the reconstructed source independently reproduces the signed AAB byte-for-byte. The signed production AAB remains the immutable reference artifact.

## Production artifact reference

- AAB: `/home/cliu/Development/release-artifacts/launch-circle-1.0.44-code46-api-capabilities-r2-2026-11-24.aab`
- SHA-256: `6d23d96b450812ea40f75577666d49881fc112ee596231c37a2a8e90e3f69db5`
- Package/version: `com.launchcircle.testers`, `1.0.44` / code `46`
- Source manifest: `evidence/launch-circle-release-candidate-source-hashes-1.0.44-46-2026-11-24.txt` (105 entries)
- Release record: `docs/RELEASE_CANDIDATE_1.0.44_46_2026-11-24.md`

## Reconstruction and verification

- Local/remote refs, tags, worktrees, reflogs, stash and unreachable Git objects were inspected. No code46 commit, tag, stash or complete alternate source checkout was found; latest available committed Android baseline was code20.
- The five initial capability-repair edits, plus the `ApiCapabilities.kt` and repository HTTP-status changes, were reversed only in temporary reconstruction files using the recorded Codex patch history. The resulting seven files were accepted only after matching their frozen manifest hashes.
- The remaining manifest paths were copied from the retained release-candidate source tree into the independent `recovery/launch-circle-code46-baseline-20261127` worktree. Final result: **105/105 SHA-256 matches**.
- The isolated worktree began at Git commit `1933ff38e2e5ba532a035561b326b91a3c533fd8` (tracked Android version code20). No files in the original shared-pool worktree were staged, reset, cleaned, or overwritten.
- The original worktree still contains its existing user changes; this recovery did not use `git add -A`.

## Limits and next check

The manifest verifies the listed Android source/build inputs. It does not establish byte-for-byte AAB reproducibility, verify every external Gradle dependency resolution, or recover a historical Git commit that never existed. Run the full local CI from this isolated baseline and record the generated artifact hash separately before creating a code47 fix commit. Do not publish this baseline as a new production release.
