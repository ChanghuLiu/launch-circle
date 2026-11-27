"""Best-effort, privacy-minimized API activity logging."""
import hashlib
import logging
import re
import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.database import SessionLocal
from app.models.activity import UserActivityEvent
from app.models.admin import AdminAudit

logger = logging.getLogger(__name__)
_cleanup_lock = threading.Lock()
_last_cleanup: datetime | None = None

_EVENTS = {
    "google_auth": ("auth.sign_in", "auth"),
    "register": ("auth.register", "auth"),
    "login": ("auth.sign_in", "auth"),
    "refresh": ("auth.session_refresh", "auth"),
    "logout": ("auth.sign_out", "auth"),
    "update_device": ("device.registered", "account"),
    "update_me": ("profile.updated", "account"),
    "update_tester_email": ("tester_email.consent_updated", "account"),
    "update_tester_group_access": ("tester_group_access.updated", "account"),
    "create_app": ("app.created", "app_setup"),
    "update_app": ("app.updated", "app_setup"),
    "confirm_google_group": ("app.group_setup_confirmed", "app_setup"),
    "upload_icon": ("app.icon_updated", "app_setup"),
    "import_icon": ("app.icon_imported", "app_setup"),
    "submit_intake": ("app.intake_submitted", "app_setup"),
    "create_additional_app_checkout": ("purchase.additional_app_checkout_started", "purchase"),
    "create_managed_checkout": ("purchase.managed_checkout_started", "purchase"),
    "verify_google_play_purchase": ("purchase.google_play_verification", "purchase"),
    "update_pool_preference": ("tester_pool.preference_updated", "tester_pool"),
    "accept_opportunity": ("app_test.accepted", "tester_pool"),
    "join_app_group": ("app_group.joined", "groups"),
    "join_app_group_for_app": ("app_group.owner_joined", "groups"),
    "leave_app_group": ("app_group.left", "groups"),
    "leave_circle": ("circle.left", "groups"),
    "confirm_opt_in": ("assignment.opt_in_confirmed", "testing"),
    "confirm_installed": ("assignment.install_confirmed", "testing"),
    "todays_assignments": ("tests.opened", "testing"),
    "todays_missions": ("missions.opened", "testing"),
    "start_mission": ("mission.started", "testing"),
    "complete_mission": ("mission.completed", "testing"),
    "submit_feedback": ("mission.feedback_submitted", "testing"),
    "complete_test_assignment": ("assignment.completion_requested", "testing"),
    "drop_assignment": ("assignment.abandoned", "testing"),
    "assign_tester": ("assignment.created", "testing"),
    "match_testers": ("assignments.matched", "testing"),
    "submit_mission_run": ("evidence.run_submitted", "evidence"),
    "record_enrollment_evidence": ("evidence.enrollment_submitted", "evidence"),
    "set_evidence_build": ("evidence.build_updated", "evidence"),
    "declare_evidence_fix": ("evidence.fix_recorded", "evidence"),
    "create_invite": ("invite.created", "invitations"),
    "create_app_invite": ("invite.created", "invitations"),
    "accept_invite": ("invite.accepted", "invitations"),
    "add_app_change": ("app.change_recorded", "app_management"),
    "record_coordination_time": ("app.coordination_time_recorded", "app_management"),
    "record_managed_offer_viewed": ("managed_offer.viewed", "app_management"),
}

_READ_EVENTS = {
    "list_apps": ("apps.opened", "app_management"),
    "get_app": ("app.opened", "app_management"),
    "list_circles": ("circles.opened", "groups"),
    "get_circle": ("circle.opened", "groups"),
    "get_app_circle": ("app.circle_opened", "groups"),
    "list_app_groups": ("app_groups.opened", "groups"),
    "app_groups_for_owned_app": ("app_group.options_opened", "groups"),
    "get_me": ("account.opened", "account"),
    "tester_group_access": ("tester_group_access.opened", "account"),
    "pool_preference": ("tester_pool.opened", "tester_pool"),
    "opportunities": ("tester_pool.opportunities_opened", "tester_pool"),
    "community_apps": ("community_apps.opened", "tester_pool"),
    "my_intakes": ("app_intakes.opened", "app_setup"),
    "app_dashboard": ("app.dashboard_opened", "app_management"),
    "list_testers": ("app.testers_opened", "app_management"),
    "app_feedback": ("app.feedback_opened", "app_management"),
    "todays_assignments": ("tests.opened", "testing"),
    "todays_missions": ("missions.opened", "testing"),
    "assignment_missions": ("assignment.missions_opened", "testing"),
    "list_my_invites": ("invites.opened", "invitations"),
}


def _safe_header(value: str | None, pattern: str, max_length: int) -> str | None:
    if not value or len(value) > max_length or not re.fullmatch(pattern, value):
        return None
    return value


def _event(route_name: str, method: str) -> tuple[str, str] | None:
    if method in {"GET", "HEAD"}:
        return _READ_EVENTS.get(route_name)
    return _EVENTS.get(route_name) or ("api.write", _workflow(route_name))


def _workflow(route_name: str) -> str:
    if any(token in route_name for token in ("mission", "assignment", "test")):
        return "testing"
    if any(token in route_name for token in ("circle", "group")):
        return "groups"
    if any(token in route_name for token in ("pool", "opportunit")):
        return "tester_pool"
    if "payment" in route_name or "checkout" in route_name:
        return "purchase"
    if "evidence" in route_name or "run" in route_name:
        return "evidence"
    if "app" in route_name or "intake" in route_name:
        return "app_setup"
    return "account"


def _safe_object(path_params: dict) -> tuple[str | None, str | None]:
    for key in ("app_id", "assignment_id", "mission_id", "group_id", "circle_id", "run_id", "checkout_id", "purchase_id"):
        value = path_params.get(key)
        if value and re.fullmatch(r"[0-9a-fA-F-]{36}", str(value)):
            return key.removesuffix("_id"), str(value)
    return None, None


def _result(status_code: int) -> tuple[str, str | None, str]:
    if status_code < 400:
        return "SUCCESS", None, "Request completed."
    codes = {
        400: ("BAD_REQUEST", "Review the submitted values and try again."),
        401: ("AUTH_REQUIRED", "The session is missing, expired or invalid."),
        402: ("PAYMENT_REQUIRED", "The requested action needs a valid purchase or entitlement."),
        403: ("ACCESS_DENIED", "The account is not authorized for this action."),
        404: ("NOT_FOUND", "The requested item is unavailable or outside this account's scope."),
        409: ("STATE_CONFLICT", "The current item state or business limit does not allow this action."),
        422: ("VALIDATION_FAILED", "One or more submitted fields failed validation."),
        429: ("RATE_LIMITED", "Too many attempts; wait and try again."),
        503: ("SERVICE_UNAVAILABLE", "A required service is temporarily unavailable."),
    }
    code, summary = codes.get(status_code, ("REQUEST_FAILED" if status_code < 500 else "SERVER_ERROR",
                                              "The request could not be completed; support can use the request ID to investigate."))
    return "FAILURE", code, summary


def _cleanup(db, current: datetime) -> None:
    global _last_cleanup
    if _last_cleanup and current - _last_cleanup < timedelta(hours=6):
        return
    if not _cleanup_lock.acquire(blocking=False):
        return
    try:
        if _last_cleanup and current - _last_cleanup < timedelta(hours=6):
            return
        db.execute(delete(UserActivityEvent).where(
            UserActivityEvent.occurred_at < current - timedelta(days=180)
        ))
        db.execute(delete(AdminAudit).where(
            AdminAudit.created_at < current - timedelta(days=365)
        ))
        _last_cleanup = current
        _last_cleanup = current
    finally:
        _cleanup_lock.release()


def record_request_activity(request, status_code: int) -> str:
    """Persist a safe request summary in a separate best-effort transaction."""
    request_id = getattr(request.state, "request_id", str(uuid4()))
    method = request.method.upper()
    route = request.scope.get("route")
    route_template = getattr(route, "path", None)
    route_name = getattr(route, "name", "")
    if not route_template or route_template.startswith("/admin"):
        return request_id
    if not route_template.startswith(("/v1/", "/apps", "/assignments", "/missions", "/circles", "/app-groups", "/tester-pool", "/test-", "/payments", "/android-version", "/pilot-config", "/auth", "/app-intakes", "/runs")):
        return request_id
    event = getattr(request.state, "activity_event", None) or _event(route_name, method)
    if event is None:
        # All endpoint failures are useful; successful reads are sampled from a named allowlist.
        if status_code < 400:
            return request_id
        event = ("api.request_failed", _workflow(route_name))
    event_name, workflow = event
    outcome, error_code, summary = _result(status_code)
    current = datetime.now(UTC)
    object_type, object_id = _safe_object(request.scope.get("path_params", {}))
    user_id = getattr(request.state, "activity_user_id", None)
    platform = _safe_header(request.headers.get("x-client-platform"), r"android|ios|web", 12) or "unknown"
    device_type = _safe_header(request.headers.get("x-device-type"), r"mobile|tablet|desktop", 12) or "unknown"
    version = _safe_header(request.headers.get("x-client-version"), r"[A-Za-z0-9._+-]+", 32)
    route_method_key = f"{method}:{route_template}"
    dedupe_key = None
    # Deduplicate repeated view events and repeated failures; never deduplicate successful writes.
    if outcome == "FAILURE" or method in {"GET", "HEAD"}:
        material = "|".join((user_id or "anonymous", event_name, workflow, outcome,
                             error_code or "", route_method_key, object_id or "",
                             str(int(current.timestamp()) // 30)))
        dedupe_key = hashlib.sha256(material.encode()).hexdigest()
    try:
        with SessionLocal() as db:
            if dedupe_key:
                prior = db.scalar(select(UserActivityEvent.id).where(
                    UserActivityEvent.dedupe_key == dedupe_key,
                    UserActivityEvent.occurred_at >= current - timedelta(seconds=30),
                ).limit(1))
                if prior:
                    return request_id
            db.add(UserActivityEvent(
                occurred_at=current,
                user_id=user_id,
                event_name=event_name,
                workflow=workflow,
                object_type=object_type,
                object_id=object_id,
                outcome=outcome,
                error_code=error_code,
                support_summary=summary,
                request_id=request_id,
                client_version=version,
                platform=platform,
                device_type=device_type,
                method=method[:8],
                route_template=route_template[:200],
                status_code=status_code,
                dedupe_key=dedupe_key,
            ))
            _cleanup(db, current)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()  # A concurrent duplicate may have won the race.
    except (SQLAlchemyError, OSError):
        logger.warning("User activity logging failed; request_id=%s", request_id)
    except Exception:
        logger.exception("Unexpected user activity logging error; request_id=%s", request_id)
    return request_id
