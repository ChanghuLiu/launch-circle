# Baseline and remaining gaps

Implementation baseline: c6491a6, branch codex/launch-circle-publisher-unlimited-1.0.8. Existing app registration, circles, assignment scheduling, billing exemption, feedback and missions were retained. No release version bump or production deployment is included.

## Operational model

Start with one shared cohort for 2–3 publishers/apps. A real person can participate in multiple apps; count that person independently for each app after joining that app. Test devices expand compatibility coverage, not participant headcount. Existing customers may supply some places; recruit additional real participants for the remaining places.

Current circles.max_members=15 includes the owner: at most 14 other testers per circle. The currently supportable buffer is 12 + 2, not 12 + 3. Expanding the capacity and its membership/billing rules needs a separate change.

## Limits

- Enrollment is self-reported or owner-confirmed, not synchronized or attested by Google.
- Recorded continuity and dates are estimates. Applicable Play requirements and eligibility must be checked in Play Console. No daily-use quota or production approval is guaranteed.
- Device keys identify reported client/lab installations, not verified physical hardware; reinstall and separate reporting clients can produce different keys. Canonical device identity is future work.
- This pilot does not automatically recruit a shared cohort, verify human uniqueness, or replace existing matching.
- Evidence UI is internal-pilot English; complete localization remains pending.
- Owner build declaration and fix/retest APIs are available; comprehensive publisher evidence management UI remains future work.
- Authentication uses existing sessions. Dedicated machine credentials are not introduced.
- Manual form metadata is reported by the client; it is not hardware attestation.
- Legacy completion records do not establish a successful core workflow.
- Large campaigns need pagination and production performance review; the current report loads campaign history.
- No 14-day real-customer campaign, Google sign-in end-to-end test, or production rollout was performed.

The technical pilot is ready for review. Customer campaign readiness still requires recruiting and confirming actual participants and completing real app-specific workflows.
