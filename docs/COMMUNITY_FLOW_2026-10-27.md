# Community testing flow

Home is the community app directory. My Launch remains a separate tab. Public cards show app icon, name, package, workflow and a Join testing button; no tester counts or private emails are published. Own apps open launch management; accepted apps open Tests.

Browsing does not assign work. A Join testing action records voluntary pool consent and one app assignment atomically, reusing the existing two-concurrent-app limit. Google Group membership, Google Play opt-in, installation and actual testing remain separate user actions. The platform never fabricates Play enrollment or eligibility.

Private developer invitations and invitation-code entry are removed from normal navigation. Creation no longer requires choosing a circle; a backend owner circle is allocated automatically. Legacy circle data remains for existing assignments.

Each ordinary authenticated user may own one app. A serialized backend check and a per-owner free-app index prevent bypass through repeated requests. Only the configured authenticated Google administrator bypasses the quota. Existing projects are retained. Additional app payment is removed from the new creation flow.

A valid test link, workflow and owner-confirmed Google Group setup automatically publish the app to the community. Removing confirmation removes the listing. Owner confirmation is a self-report, not independent verification of Play Console. Existing configured projects were listed during deployment.

Limits: external publishers still require the existing package ownership verification/onboarding process. Credits and paid testing packs were not introduced. Community membership does not guarantee twelve volunteers.

Validation: 42 backend tests passed across shared pool, admin, entitlements, circles and assignments. Android debug build passed. Live API deployed with a database and code backup. Device checks recorded separately.
