# Voluntary shared tester pool

The shared pool removes the requirement that a customer first recruit enough other paying publishers into their own circle. Existing authenticated users can volunteer, discover owner-published apps and explicitly accept each app's tasks. A pool member is not assigned to other apps through their circle membership: automatic matching and replacement exclude registered pool users.

Owner: open Shared tester pool, then Open recruitment for an app. Confirm the Google Group, Play testing link and core workflow first. Listing publishes the app name, package and workflow to volunteers; never put credentials in those steps. Closing recruitment preserves existing tasks.

Tester: choose Join voluntary tester pool, inspect an opportunity and Accept this app's tasks. Return to Today's tests for separate Google Play opt-in and installation confirmations. Pausing the pool stops new acceptances and preserves existing tasks and Play opt-ins. Existing drop/leave actions remain available.

Capacity: owner plus 14 other circle members; at most two unfinished apps per volunteer across all circles. Completed mission assignments still reserve capacity while their app is in a live testing state. Fourteen volunteers can cover two 14-person campaigns, not twelve. The 1–12-customer parameterized tests provision separate volunteer cohorts per pair of apps (84 volunteers for twelve simultaneous apps). These fixtures are synthetic, not evidence of actual customers, people or Google qualification.

Supply displays accepted assignments and separately reported Play opt-in plus installation. Both are internal records; Google eligibility is always unconfirmed. Start and continuation must be reconciled with the customer's own Play Console.

No users, invitations, customer apps or opt-ins are seeded into production. Pool consent and listings default off. Genuine tester recruitment and per-customer Play permissions remain operational requirements. Existing app registration, publisher identity and Billing checks are unchanged.

Additive schema: tester_pool_preferences and pool_listings, with user/app deletion cascades; migration 0016 follows the existing additive evidence migration. SQLite accepts are serialized before quota reads. Tests cover concurrent app/circle limits, idempotency, consent revocation, scope checks and deletion.

Android 1.0.9 (11), minSdk 27, keeps Google Play Billing and existing app identity. The evidence pilot remains disabled unless separately configured.

## Verification before publication

107 backend tests passed, including 17 shared-pool cases. The synthetic 1–12-customer matrix, concurrent capacity checks, consent isolation and account-deletion cascades passed. Empty SQLite upgrade and 0016 downgrade/re-upgrade passed. Scoped Ruff and whitespace checks passed. Android 34 unit tests, debug build/lint and signed release bundle passed. Real Google sign-in and a real 14-day external customer campaign are not established by these checks.
