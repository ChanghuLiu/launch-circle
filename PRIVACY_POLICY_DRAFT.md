# Launch Circle Privacy Policy — Draft

**Product:** Launch Circle: 12 Testers  
**Status:** Draft for review; not yet published  
**Last updated:** August 19, 2026

Launch Circle helps Android developers coordinate closed testing. This draft describes the data handled by the current Android application and FastAPI service. A public policy URL must be published before Google Play submission. Privacy requests may be sent to cliu@tradewind.aero.

## Data we collect

When you use Launch Circle, the service may collect and store:

- Google account identity: Google account identifier, email address, and display name supplied through Google Sign-In.
- Profile information you provide: display name, country, languages, tester email, and tester-email sharing consent.
- Device information: app-generated random installation identifier, manufacturer, model, Android API version, declared capabilities, and last-seen time.
- Developer app information: app name, package name, Google Play closed-testing opt-in URL, Google Group choice, setup confirmation, and testing dates.
- Testing activity: tester assignments, opt-in and installation confirmations, mission availability and completion, tester health state, reliability state, replacement history, and related timestamps.
- User-generated content: ratings, issue reports, suggestions, final feedback, and developer-recorded changes.
- Invite and operational activity: invite codes, optional invited email, invite acceptance, and product events such as assignment, mission, feedback, and group-confirmation events.
- Authentication/session data: access and refresh tokens. Refresh tokens are stored hashed by the backend; session tokens are stored in private app storage on the device.

The release app does not request precise location, contacts, photos, microphone, camera, advertising ID, financial information, or health information.

## How we use data

We use recorded data to:

- authenticate accounts and maintain sessions;
- operate tester matching and the 14-day testing workflow;
- show launch, tester, mission, feedback, and readiness status;
- create invites and record Google Group setup confirmation;
- detect inactive or at-risk testing assignments and arrange replacements;
- generate testing summaries and production-access preparation material based on recorded facts;
- protect reliability and integrity of the pilot service.

Launch Circle does not sell personal data, serve advertising, or claim affiliation with Google. Launch Circle does not guarantee Google Play production approval.

## Sharing

Data is sent to the Launch Circle FastAPI service over HTTPS. Google processes Google Sign-In and Google Group interactions under its own policies. Google Play testing links open Google Play.

App owners normally see tester labels and testing progress rather than tester email addresses. Information may be disclosed when required by law or to infrastructure providers strictly needed to operate the service. The final public policy must identify those providers before publication.

## Storage, security, and retention

Release traffic uses HTTPS. The Android app disables system backup and stores session data in app-private storage. The pilot backend stores application records in a protected SQLite database with controlled backups.

Authenticated users can permanently delete their account and associated active-service data from Account / Settings. An email fallback is available at cliu@tradewind.aero. Limited copies may remain temporarily in protected backups or when retention is required for security or legal obligations. A specific routine retention schedule is not yet finalized and must be reviewed before publication.

## Your choices

You may decline optional profile fields and tester-email sharing consent. You may sign out to remove the local session. You may permanently delete your Launch Circle account in Account / Settings, or contact cliu@tradewind.aero if you cannot access the app.

## Children

Launch Circle is intended for adult Android developers and is not directed to children under 13.

## Changes

Material policy changes should be posted at the public privacy-policy URL with an updated date.
