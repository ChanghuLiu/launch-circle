"""Account-scoped group attestation; never claims Google membership verification."""
from fastapi import HTTPException
from app.core.config import get_settings


def group_access_status(user):
    if user.tester_group_url != get_settings().launch_circle_google_group_join_url:
        return "NOT_JOINED"
    if user.tester_group_status == "SELF_CONFIRMED" and not (user.tester_group_play_email and user.tester_group_confirmed_at):
        return "NOT_JOINED"
    return user.tester_group_status


def require_tester_group(user):
    if group_access_status(user) != "SELF_CONFIRMED":
        raise HTTPException(409, "Join the Launch Circle Google Group first, then confirm your Play account in Tests. Pending approval is not membership.")


def require_test_enrollment(user, assignment):
    require_tester_group(user)
    if assignment.play_account_email != user.tester_group_play_email or not assignment.opted_in_at or not assignment.installed_at or assignment.status not in {"ACTIVE", "INSTALLED", "COMPLETED"}:
        raise HTTPException(409, "Join this app's Play test and confirm installation before testing.")
