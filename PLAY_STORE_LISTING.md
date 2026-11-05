# Google Play listing preparation

## Core listing

**App name**  
Launch Circle: 12 Testers

**Short description**  
Plan Android beta tests with missions, private feedback, and retest tracking.

**Full description**

Launch Circle helps Android developers organize useful closed-test QA with other developers.

Create a testing circle or browse available tests. Review each app's purpose and requested tasks, then choose whether to participate.

Use the official Google Play opt-in flow, try the requested app journeys as a real user, and send honest, private feedback. Follow focused missions for first impressions, core features, edge cases, second use, retesting, and final feedback. Developers can track tester status, mission and feedback progress, issues, changes made from feedback, and a testing summary based on recorded evidence.

Participation is voluntary. When developers agree to a reciprocal test, each contributes real testing and private feedback for the other. No cash or credits are offered for installs, and store ratings or reviews are not requested or exchanged. Tester availability and engagement vary. Launch Circle does not guarantee a tester count, 14 continuous days, production access, or Google approval. Launch Circle is not affiliated with or endorsed by Google.

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
3. Launch Dashboard — test progress, tester status, Day X/14, and circle health. Avoid suggesting that listing 15 seats guarantees 15 active testers.
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
