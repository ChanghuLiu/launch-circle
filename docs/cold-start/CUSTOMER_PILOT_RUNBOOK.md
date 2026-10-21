# Customer pilot handoff

Status: technical workflows implemented; no real customer campaign has started.

## Required real inputs

| Campaign | Required inputs before activation | Current status |
| --- | --- | --- |
| App A | Owner, package, live Play testing link, candidate version, 3–5 meaningful steps | Not supplied for a real campaign |
| App B | Same inputs, independently confirmed | Not supplied |
| App C (optional) | Same inputs, independently confirmed | Not supplied |
| Shared cohort | Real participants consenting to each app, contact/enrollment confirmation | No real roster supplied |

The internal Notes Escape pilot observations and the labeled synthetic UI fixture are not a customer campaign. Never import fixture users or generated failures into a real report.

## Start with 2–3 existing customers

1. Ask each publisher to supply the inputs above. Use existing customers for some participant places where appropriate and recruit additional real participants. A shared pool can test multiple apps, joining each independently.
2. Current circles permit the owner plus 14 other people. Plan 12 participants plus 2 reserves within that capacity. Do not substitute phones, extra accounts controlled by one operator, assisted runs or synthetic users for recruited participants.
3. Verify that each participant can open the correct Play testing link, join that app, and install its candidate build. Record observations with their actual source. The app cannot verify Google enrollment directly.
4. For each app, open My Launch → Testing evidence and set its candidate version. Explain the core workflow and expected behavior. Do not publish private credentials in step text or reports.
5. Follow the existing mission schedule (days 1, 3, 5, 8, 11, 14). This schedule is a product workflow, not a claim that Google requires daily check-ins.
6. Review failures. Read recorded steps, publish a real fix, declare its version, and set that version as the candidate. Open the failure details and repeat the original observations. A passing retest verifies that recorded scope only.
7. Prepare a fresh report after updates. Save JSON for exact records or the readable report for review. Share only through the user-selected destination.
8. Reconcile the real roster and continuity with Play Console before any production-access request. Report actual engagement and changes; never reuse synthetic fixture outcomes as customer feedback.

## Source and applicability

Google's official guidance, checked 2026-10-21: personal developer accounts created after 2023-11-13 must complete a closed test with at least 12 testers continuously opted in for 14 days before applying for production access. Leaving and rejoining restarts that participant's continuity. Meeting these criteria allows an application; it does not guarantee approval.

Source: https://support.google.com/googleplay/android-developer/answer/14151465?hl=en

The app's enrollment dates are evidence estimates, not a Google synchronization. Use the requirements shown in the actual publisher's Play Console.

## Handoff boundary

No invitation has been sent, no production rollout has occurred, and no 14-day real-participant period has elapsed. Actual app links and a real participant roster are the remaining inputs required to start the customer pilot. Keep the new functionality default-off outside the isolated technical pilot until rollout is reviewed.
