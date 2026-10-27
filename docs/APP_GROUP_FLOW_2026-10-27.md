# App Group flow (supersedes flat community home)

Home shows persistent App Groups and their app lists. A published app is automatically matched to an open group of at most 15 distinct owners. A manager may publish multiple apps, but they cannot occupy multiple app slots in the same group. Group app counts are not active tester counts.

The app owner opens the matched group and explicitly joins. The consent covers current and future group apps, up to 14 other developers. Only then are test assignments created. Joining is idempotent and never fabricates Google opt-in, installation, feedback or 14-day eligibility. A forming group can start testing with fewer members but does not yet provide 12 testers. Actual participation is voluntary and not guaranteed.

Existing outside assignments are retained. Group synchronization respects 14 concurrent tasks and skips capacity-constrained apps without deleting or completing existing work. Apps retain their original internal circles and assignments; platform App Groups are independent of Google Groups. The guided enrollment screen supplies the app's Google Group link for first-time members.

Feedback state is supplied on both assignment and mission responses. A submitted mission cannot be reopened. If no other available/completed-but-unsubmitted mission remains, the assignment appears in Completed with Feedback submitted and has no Start button. A future due mission reopens the assignment. Completing a mission without successfully submitting feedback remains recoverable.

Validation: 35 tests passed for groups, pool, assignments, person quotas and assisted intake; 11 tests passed for groups and administrator regression (44 distinct tests including the subsequent cross-day task regression). Android build passed. Deployment preserved code/database backups. Four existing listed apps were matched to one forming group. No group participation was silently granted. ID12 explicitly joined during assisted device QA and received three other-app tasks. ID1 completed cards were tapped and remained on Tests without reopening a task. Durable App Group assignments remain visible across days without daily copies.


## Capacity, departure and UI review

- Full means 15 reserved developer/app slots. It stops new app matching, not history access or existing member confirmations. Reserved slots are not a claim of fifteen active testers.
- Pausing recruitment retains the slot and current tasks. Public occupancy is based on all reserved slots, while app details exclude paused listings; the owner can still find and leave the group.
- Leaving requires confirmation. It removes membership and the owner's slot, pauses the listing, drops unfinished reciprocal group assignments, releases unused non-owner internal memberships and recalculates coverage. Feedback, completed history and Google Play opt-in are preserved as records; no Google membership is changed automatically.
- New apps fill reopened slots. Resuming recruitment rematches the app. Same-group rejoining restores only assignments dropped by that group-exit event, preserving their IDs/history and honoring workload/circle limits. If the old slot has been filled, a new group is selected.
- Completed group join and Play setup confirmations are disabled. Completed feedback tasks stay disabled; navigation to feedback/history remains available. Empty feedback navigation is disabled.
- Main actions are separated from settings. App icon editing moves into collapsible app settings. Coverage is condensed. Rules are collapsible and group entry appears before long member previews.
- Mission progression waits for successful network completion. Save/confirm/start buttons are disabled while loading, and Add App blocks duplicate creation clicks. Single-line app identity fields prevent accidental multi-line input.

This review validated 39 backend tests across groups, shared pool, assignments and lifecycle; amended full-group replacement/resume scenarios passed in a focused 12-test rerun, and reserved-slot cases passed in the six group tests. Android build passed. ID1/ID12 updated; actual departure was tested only with synthetic fixtures. ID12's leave dialog was inspected and cancelled, preserving the real membership.

Phone review also found the legacy Healthy/Good label with zero testers. My Launch now shows Waiting for testers to join and install, places setup/group/recruitment actions before the progress summary, and keeps completed setup disabled.
