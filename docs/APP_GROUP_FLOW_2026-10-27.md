# App Group flow (supersedes flat community home)

Home shows persistent App Groups and their app lists. A published app is automatically matched to an open group of at most 13 distinct owners. A manager may publish multiple apps, but they cannot occupy multiple app slots in the same group. Group app counts are not active tester counts.

The app owner opens the matched group and explicitly joins. The consent covers current and future group apps, up to 12 other developers. Only then are test assignments created. Joining is idempotent and never fabricates Google opt-in, installation, feedback or 14-day eligibility. A forming group can start testing with fewer members but does not yet provide 12 testers. Actual participation is voluntary and not guaranteed.

Existing outside assignments are retained. Group synchronization respects 12 concurrent tasks and skips capacity-constrained apps without deleting or completing existing work. Apps retain their original internal circles and assignments; platform App Groups are independent of Google Groups. The guided enrollment screen supplies the app's Google Group link for first-time members.

Feedback state is supplied on both assignment and mission responses. A submitted mission cannot be reopened. If no other available/completed-but-unsubmitted mission remains, the assignment appears in Completed with Feedback submitted and has no Start button. A future due mission reopens the assignment. Completing a mission without successfully submitting feedback remains recoverable.

Validation: 35 tests passed for groups, pool, assignments, person quotas and assisted intake; 11 tests passed for groups and administrator regression (44 distinct tests including the subsequent cross-day task regression). Android build passed. Deployment preserved code/database backups. Four existing listed apps were matched to one forming group. No group participation was silently granted. ID12 explicitly joined during assisted device QA and received three other-app tasks. ID1 completed cards were tapped and remained on Tests without reopening a task. Durable App Group assignments remain visible across days without daily copies.
