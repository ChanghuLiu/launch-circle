import asyncio
import logging
from datetime import UTC, datetime
from uuid import uuid4

from starlette.background import BackgroundTask

from app.core.database import SessionLocal
from app.models.admin import AdminAudit
from app.services.activity_logging import record_request_activity

logger = logging.getLogger(__name__)


def _safe_record_activity(request, status_code):
    try:
        record_request_activity(request, status_code)
    except Exception:
        logger.exception("Activity instrumentation failed; request_id=%s",
                         getattr(request.state, "request_id", "unknown"))


async def user_activity_middleware(request, call_next):
    # Generate correlation IDs server-side; never persist arbitrary client header values.
    request_id = str(uuid4())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        asyncio.get_running_loop().create_task(
            asyncio.to_thread(_record_request_result, request, 500)
        )
        raise
    response.headers["X-Request-ID"] = request_id
    existing_background = response.background

    async def record_after_response():
        # Persist diagnostics after the response body is sent so database
        # latency cannot delay the user's successful or failed action.
        await asyncio.to_thread(_record_request_result, request, response.status_code)
        if existing_background is not None:
            await existing_background()

    response.background = BackgroundTask(record_after_response)
    return response


def _record_request_result(request, status_code):
    _safe_record_activity(request, status_code)
    if status_code >= 400:
        _record_admin_failure(request, status_code)


def _record_admin_failure(request, status_code):
    if not getattr(request.state, "admin_authenticated", False):
        return
    try:
        with SessionLocal() as db:
            db.add(AdminAudit(
                created_at=datetime.now(UTC),
                action="ADMIN_REQUEST_FAILED",
                target_id=request.scope.get("route").path if request.scope.get("route") else "admin",
                detail={"actor": "operator", "result": "FAILURE", "status_code": status_code,
                        "request_id": getattr(request.state, "request_id", None)},
            ))
            db.commit()
    except Exception:  # noqa: BLE001 - audit failure must not mask the request failure
        # Logging must never turn an otherwise handled response into a failure.
        logger.warning("Operator audit logging failed; request_id=%s",
                       getattr(request.state, "request_id", "unknown"))
        return
