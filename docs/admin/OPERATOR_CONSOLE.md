# Launch Circle operator console

Production entry: https://launchcircle-api.duckdns.org/admin

## Daily use

1. Open the entry and enter the separately generated operator password. The browser receives an HttpOnly, SameSite=Strict, Secure production cookie lasting eight hours. No customer Google account or Android update is needed.
2. Refresh to retrieve current data. Search by customer name, login email, app name or package. User-reported opt-in/installation is separate from platform mission/feedback activity and from Google eligibility, which is never marked confirmed here.
3. Classify existing apps as CUSTOMER, OWN, SYNTHETIC or UNCLASSIFIED. Only explicitly classified CUSTOMER owners count as customers. Existing records default to UNCLASSIFIED. Own apps remain eligible for voluntary testing; synthetic apps cannot enter the real shared pool.
4. In an app's settings, set priority 0–100 (higher first), notes and a pause for new acceptances. Suggested priorities are customer=80, own=20. Pausing preserves all existing assignments and does not alter Google opt-in.
5. In 人工调度, recommend a ready, owner-listed app to an active volunteer who has fewer than two concurrent apps. The suggestion sorts first for that tester in the existing Android Shared tester pool screen. They must open/refresh that screen and accept. Recommendations do not reserve seats or create assignments, installations or Google enrollment. Canceling a recommendation never drops accepted work. No email, push or external invitation is sent.
6. Review each app's feedback and installation/test records. An empty record means missing platform evidence, not proof of no real usage.
7. The intake list is read-only. Package-control proof and first-app entitlements still use the existing `scripts/review_app_intake.py` operator process. The console does not bypass publisher ownership or Billing.

## Access and recovery

`ADMIN_PASSWORD_HASH` is a salted scrypt digest kept in a separate mode-600 server environment file. It is not a Google credential. The plaintext credential is generated once into a private operator access file on TradeWind, never committed or logged.

To create credentials on an authorized operator workstation, from launch-circle-api:

```
PYTHONPATH=. python scripts/configure_operator.py \
  --output-env /absolute/private/admin.env \
  --access-file /absolute/private/Launch-Circle-Admin.txt
```

The directories must already exist. The utility refuses overwrite; use `--rotate` intentionally to rotate. Install the digest file into the service's separate EnvironmentFile, restart, and keep the new access file private. Rotation invalidates existing sessions because session lookup incorporates the current password digest. Removing the setting disables all operator data access.

One operator identity is supported. Session hashes, expiry and sanitized action audits are persisted. App controls and recommendation changes record before/after or target details, without credentials. Login accepts at most ten attempts per minute per API process. Write endpoints require a custom same-origin header and reject foreign Origin. No-store, CSP, frame denial and noindex are set on console responses. No external scripts/CDNs, localStorage tokens, or HTML rendering of user-provided strings.

## Limits and validation

The overview explicitly warns when exceeding 500 users, 500 apps or 2,000 assignments. Intake and feedback show the latest 200; audit shows the latest 100. This is a small pilot operations console, not a production analytics warehouse. No payment, account deletion, installation verification override or forced reassignment controls.

Validated: seven new integration tests plus the existing suite (117 total); session/ordinary-user boundaries, CSRF, expiry, production cookie, credential rotation, rate limit, recommendation idempotency/order, consent and concurrency caps, classification, pause preserving work, assets/headers. Headless Chromium exercised login, dispatch/revoke, settings, feedback, all tabs, search and logout; inspected screenshots at 1440px and 390px with no horizontal viewport overflow. Synthetic QA is isolated from the production database and phones. Additive 0018 migration supports empty upgrade and down/up; production copy validation retains existing table counts and SQLite integrity/FKs.
