# Required Android updates

Version 1.0.13 / code 15 adds an app-wide update gate before onboarding and authentication. Checks run on foreground entry and every five minutes while active. A higher server versionCode blocks app use; equal or newer builds pass. Connection errors and a 12-second timeout show Retry instead of bypassing the check. Returning from an update rechecks. The check overlay keeps existing forms mounted.

GET /android-version?channel=play|direct is public and sends Cache-Control: no-store. Channels must remain separate: a debug APK has a different signing certificate from the Google Play build.

- Play: ANDROID_LATEST_VERSION_CODE, ANDROID_LATEST_VERSION_NAME. Raise only after that release is available to the intended Play audience. Update opens the app's Play listing.
- Independent test APK: ANDROID_DIRECT_LATEST_VERSION_CODE, ANDROID_DIRECT_LATEST_VERSION_NAME, ANDROID_APK_PATH. Upload a verified same-package/same-signing-key APK first, then raise the version requirement. GET /android-update.apk serves only the configured file. Android/browser download and installation confirmations remain required; app data need not be removed.

Current deployed direct build: 1.0.13/code 15. Play requirement remains unchanged. This feature cannot retroactively add a gate to old installations that never contained this code; install this baseline first. Never advertise an unavailable build or a lower-code APK at the update endpoint.

Validation: public policy, no-cache header, separate channels, invalid channel rejection, configured-file downloads, version comparison; ID12 code 14 was blocked with code 15 available and the update button opened the APK download prompt. Same-signature ADB replacement is used for controlled device validation.
