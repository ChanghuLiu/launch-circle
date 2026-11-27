# Launch Circle code47 local CI — 2026-11-27

Candidate source commit before the CI-support adjustment: `99decbe` (`fix(android): recover capabilities state and prepare code47`).

## Results

- Android: `:app:testDebugUnitTest`, `:app:assembleDebug`, and `:app:lintDebug` passed with `launchCircleEvidencePilotBuild=true`; 45 unit tests, 0 failures/errors/skips.
- Backend: full pytest suite passed, **177 passed** (9 existing collection/deprecation warnings).
- Backend Ruff: the exact workflow lint scope passed.
- Alembic: a new disposable SQLite database upgraded from empty to `0021_group_task_queue` successfully. No production database was touched.
- Git whitespace check passed.

## CI-support changes

The restored API/test baseline had a small set of workflow-scope mismatches: safe import/order formatting and explicit exports for the App Group ORM re-exports; backend test request bodies were brought into line with the API's required audit-reason fields. The local SQLite backup helper now sets the completed backup to mode `0600`, as required by its existing regression test. These are isolated in a separate commit from the Android capabilities fix; no production backup was run or changed.

This local result is not the hosted GitHub Actions result. The latter must be recorded separately after the release branch is pushed and the workflow completes.
