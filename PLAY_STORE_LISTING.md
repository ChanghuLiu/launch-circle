# Google Play listing preparation

## Core listing

**App name**  
Launch Circle: 12 Testers

**Short description**  
Find Android testers and manage your 14-day closed testing workflow.

**Full description**

Launch Circle helps Android developers organize the work required for a meaningful Google Play closed test.

Find available developers, invite people to your testing circle, and track progress toward the 12-tester minimum. A 15-tester target provides room for inactive or dropped testers while keeping the launch useful even when the community is still growing.

Follow a coordinated 14-day workflow with focused missions for first impressions, core features, edge cases, second use, retesting, and final feedback. Testers confirm opt-in and installation, complete currently available missions, and submit factual issues and suggestions.

Developers can monitor active, new, at-risk, inactive, dropped, and replacement testers; review mission and feedback progress; record changes made from feedback; and prepare a production testing summary based on stored evidence.

Launch Circle supports production access preparation. It does not access your Play Console, submit applications for you, guarantee production access, or guarantee Google approval. Launch Circle is not affiliated with or endorsed by Google.

## Play Console recommendations

- Category: Tools
- Target audience: Adults / 18 and over; not designed for children
- Ads: No, the app contains no ads or advertising SDK
- App access: Some or all functionality is restricted by Google Sign-In. Supply Play review access instructions and a working reviewer account if OAuth is restricted to test users. Explain that the reviewer signs in, completes the short onboarding, and can inspect launches and available tests.
- Content rating notes: No violence, sexual content, gambling, controlled substances, or profanity is supplied by the app. Users can submit private testing feedback and suggestions; there is no chat, public social feed, or user-to-user media sharing. The final rating is determined by the Play questionnaire.

## Data Safety working summary

Data collected and sent to the Launch Circle backend:

- Personal info: email address, name, optional country/languages, optional tester email
- User IDs: Google account subject and Launch Circle account identifiers
- Device or other IDs: app-generated random installation identifier
- Device information: manufacturer, model, and Android OS/API version
- App activity: sign-in/session activity, tester assignments, opt-in/install confirmations, mission activity, tester status, invites, and operational events
- User-generated content: feedback, issue descriptions, suggestions, and developer-recorded changes
- Developer-provided app data: app/package names, Play testing links, Google Group setup, and testing dates

Primary purposes: app functionality, account management, testing coordination, service reliability, and production-access preparation. No ads, data sale, or advertising purpose is implemented. Data is encrypted in transit for the release build. Authenticated users can delete their account in the app, with an email fallback. The public privacy-policy and account-deletion URLs must be live, and the retention wording must be reviewed, before the final Data Safety submission.

## Store assets

Do not upload existing acceptance screenshots. They contain seeded app names, acceptance state, debug/local-login context, or evidence-only UI.

Recapture clean portrait screenshots from the release-configured build with sanitized realistic data:

1. First onboarding screen — product promise, no debug controls.
2. My Launches — one healthy launch and one early/cold-start launch.
3. Launch Dashboard — readiness, 13/15 testers, Day X/14, and circle health.
4. Invite Developer — use a nonfunctional example invite code/link.
5. Tester Status — active, new, needs-attention, replacement, and dropped states without emails.
6. Today Tests — meaningful available missions without acceptance labels.
7. Optional Google Group setup — shared group instructions and confirmation state.

Additional assets still required:

- Play high-resolution icon, 512 x 512 PNG derived from the approved artwork
- Feature graphic, 1024 x 500, with release-safe branding
- At least two clean phone screenshots; six are recommended above
- Public privacy-policy URL

Screenshots must not show test credentials, localhost/LAN URLs, acceptance wording, internal IDs, debug buttons, notification bars with private information, or fabricated approval claims.
