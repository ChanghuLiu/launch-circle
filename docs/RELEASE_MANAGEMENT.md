# Launch Circle Android release traceability

Every Google Play Android release must have a committed source baseline and a durable release record before production upload.

## Required links

For each release, record all of the following in `launch-circle-android/releases/`:

1. **Source identity:** Git commit SHA that was built; the release branch/tag must resolve to that commit. Do not ship from an uncommitted or dirty worktree.
2. **Version identity:** `applicationId`, `versionName`, and `versionCode` read from the committed Gradle source. Version codes are monotonically increasing and must be checked as unused in Play Console immediately before candidate creation/upload.
3. **Build identity:** exact artifact filename, format (AAB/APK), SHA-256, build command/toolchain, and CI run URL/result. Keep the artifact immutable after hashing.
4. **Play identity:** package, track, version code/name, rollout percentage, submission/availability timestamps, release status, and Console readback evidence. Mark uploaded, submitted, approved, and available as separate states.
5. **Evidence:** source/build verification and relevant device acceptance. Record blockers and unverified flows plainly. Never imply a reconstructed baseline is byte-identical to a Play artifact without reproducible verification.

## Release sequence

- Start from a clean committed source ref. If recovering a historical baseline, document its provenance and hash verification in a separate commit before feature changes.
- Verify the candidate version code is not already present in Play Console and no conflicting draft exists. Save the dated readback in the release record.
- Make the fix and version bump in a dedicated commit. Run the complete CI workflow against that commit. Build the release artifact from that same commit only after required tests pass.
- Compute SHA-256 after the build and add it to a separate release-record commit that references the exact source commit and CI run. Recompute neither source nor artifact to “match” the record.
- Upload only the recorded artifact. After each Play transition, read the Console state back and append the observed status to the same release record.
- Do not use broad staging (`git add -A`) for release work; stage an explicit reviewed path list.
