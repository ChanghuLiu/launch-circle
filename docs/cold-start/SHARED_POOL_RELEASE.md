# Voluntary shared tester pool

The shared pool removes the requirement that a customer first recruit enough other paying publishers into their own circle. Existing authenticated users can volunteer, discover owner-published apps and explicitly accept each app's tasks. A pool member is not assigned to other apps through their circle membership: automatic matching and replacement exclude registered pool users.

Owner: open Shared tester pool, then Open recruitment for an app. Confirm the Google Group, Play testing link and core workflow first. Listing publishes the app name, package and workflow to volunteers; never put credentials in those steps. Closing recruitment preserves existing tasks.

Tester: choose Join voluntary tester pool, inspect an opportunity and Accept this app's tasks. Return to Today's tests for separate Google Play opt-in and installation confirmations. Pausing the pool stops new acceptances and preserves existing tasks and Play opt-ins. Existing drop/leave actions remain available.

Capacity: owner plus 14 other circle members; at most two unfinished apps per volunteer across all circles. Completed mission assignments still reserve capacity while their app is in a live testing state. Fourteen volunteers can cover two 14-person campaigns, not twelve. The 1–12-customer parameterized tests provision separate volunteer cohorts per pair of apps (84 volunteers for twelve simultaneous apps). These fixtures are synthetic, not evidence of actual customers, people or Google qualification.

Supply displays accepted assignments and separately reported Play opt-in plus installation. Both are internal records; Google eligibility is always unconfirmed. Start and continuation must be reconciled with the customer's own Play Console.

No users, invitations, customer apps or opt-ins are seeded into production. Pool consent and listings default off. Genuine tester recruitment and per-customer Play permissions remain operational requirements. Existing app registration, publisher identity and Billing checks are unchanged.

Additive schema: tester_pool_preferences and pool_listings, with user/app deletion cascades; migration 0016 follows the existing additive evidence migration. SQLite accepts are serialized before quota reads. Tests cover concurrent app/circle limits, idempotency, consent revocation, scope checks and deletion.

Android 1.0.10 (12), minSdk 27, keeps Google Play Billing and existing app identity. The evidence pilot remains disabled unless separately configured.

## Verification before publication

110 backend tests passed, including 17 shared-pool cases. The synthetic 1–12-customer matrix, concurrent capacity checks, consent isolation and account-deletion cascades passed. Empty SQLite upgrade and 0016 downgrade/re-upgrade passed. Scoped Ruff and whitespace checks passed. Android 34 unit tests, debug build/lint and signed release bundle passed. Real Google sign-in and a real 14-day external customer campaign are not established by these checks.

## Assisted onboarding for an external publisher

The production automatic registration route is scoped to the connected Play publisher. The new private assisted intake avoids bypassing that check: a signed-in external publisher can submit app name, package, claimed numeric publisher ID and 1–5 core steps. Submission creates a PENDING request, not an app, a verified identity or an entitlement. Requests are visible only to their submitter; two pending requests per user are allowed.

An authorized server operator must independently review proof that the customer controls the package and is authorized to act for the claimed publisher. Obtain evidence through an agreed secure support channel, not passwords, private keys or a public workflow field. Keep the evidence file private with mode 600. The local review command requires an existing absolute SQLite path, request ID, reviewer, reviewed proof file and redacted conclusion. There is no remotely callable approval endpoint.

Example command shape (all placeholders must be replaced from real reviewed records):

    PYTHONPATH=. python scripts/review_app_intake.py --database-path /absolute/live/database.db --request-id REQUEST_ID --reviewer OPERATOR --proof-file /private/customer-authorization.pdf --note "Reviewed customer authorization and publisher/package association"

Approval records reviewer, timestamp, proof hash and conclusion, then provisions only an unused publisher first-app entitlement. It does not mark the claimed numeric publisher identity Google-verified or grant unlimited registration. Existing Additional App/Billing checks remain in force; a used first-app entitlement is refused. The approved app appears in My Launch with Google Group unconfirmed and recruitment closed. Those access and recruitment decisions still require explicit owner action.

Schema migration 0017 adds private app_intakes with account deletion cascade and app removal SET NULL. Three new tests cover private/idempotent external intake, pending limits and deletion, local reviewed provisioning/replay, unverified identity, refusal to bypass used entitlements, and validation/no public approval endpoint.


## Final isolated UI verification

The Android emulator successfully opted a synthetic tester into the pool, accepted a synthetic app and handed it to Today's tests; the database retained ASSIGNED with no Play opt-in/install timestamps. The emulator submitted a private external-publisher intake and it remained PENDING without an app. The local operator CLI, using a clearly synthetic private proof file on an isolated test database, approved that fixture: the app appeared in My Launch, its Google Group remained unconfirmed and the publisher identity remained UNVERIFIED. These are synthetic workflow checks, not a real customer authorization or campaign.

Operator queue inspection: run scripts/review_app_intake.py with --database-path pointing to the existing live SQLite file and --list-pending. Approval requires the additional reviewed evidence arguments documented above. No invitation or external support message is sent by these tools.


## Workspace refresh regression

Returning from the shared pool now refreshes the main workspace, for both the on-screen Back button and system Back. The isolated emulator started with zero owned apps, stayed on the pool screen while a synthetic request was approved, then returned without signing out: the newly approved app immediately appeared with zero reported testers and the true missing-to-12 count. This fixes the stale workspace found during publication verification.

Version 1.0.10 (12) supersedes the initially submitted 1.0.9 (11). The backend source remains 387f252 because this follow-up changes only Android navigation/refresh and version metadata.
