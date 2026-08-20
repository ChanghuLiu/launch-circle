# Launch Circle Google Play Closed Testing release

This checklist prepares Launch Circle itself for a closed test. It does not authorize an upload or publication.

## Release configuration

- Package: `com.launchcircle.testers`
- App name: `Launch Circle: 12 Testers`
- Backend: `https://launchcircle-api.duckdns.org/`
- Authentication: Google Sign-In using the configured Web OAuth client ID
- Demo repository: disabled in release
- Development authentication: disabled in release
- Shared Google Group: `launch-circle-12-testers@googlegroups.com`

## Signing prerequisite

Create a dedicated Launch Circle upload keystore in a protected local location. Record the keystore path, key alias, store password, and key password outside Git. Add an ignored local signing properties file or inject values through environment variables. Back up the upload key securely. Never reuse another applications key and never commit the keystore or passwords.

After signing is configured, run the release checks and produce the signed bundle with `./gradlew bundleRelease`. Verify the AAB signature and configuration before upload.

## Play Console steps

1. Create the app using package `com.launchcircle.testers` and app name `Launch Circle: 12 Testers`.
2. Complete App content: privacy policy, Data Safety, ads, app access, target audience, and content rating.
3. Upload the signed release AAB to **Testing > Closed testing** and create a release.
4. Add release notes that accurately describe the closed-testing pilot.
5. In the closed track tester configuration, select Google Groups.
6. Add `launch-circle-12-testers@googlegroups.com` and save the tester list.
7. Review countries/regions and the closed-track release; do not use production.
8. Start/publish the closed test after Play Console validation succeeds.
9. Copy the Google Play opt-in link generated for this closed track.
10. Have pilot developers join the Google Group with the same Google account used on Play.
11. Open the opt-in link, accept the test invitation, and install Launch Circle from Google Play.
12. Verify Google Sign-In, onboarding, backend connectivity, invite-code entry, and one real testing workflow from the Play-installed build.

Launch Circle cannot add the group to Play Console automatically and does not guarantee production approval.
