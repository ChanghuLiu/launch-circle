"""Opt-in pilot evidence APIs. They do not assert Google eligibility or grant rewards."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.evidence import CampaignBuild, EnrollmentEvidence, MissionRun, MissionRunFix
from app.models.launch import App, TesterAssignment, TestMission
from app.models.user import User
from app.schemas.evidence import (
    EnrollmentEvidenceCreate,
    EnrollmentEvidenceRead,
    MissionRunCreate,
    MissionRunFixCreate,
    MissionRunRead,
)
from app.services.clock import aware, get_now
from app.services.missions import mission_instructions, refresh_mission_availability


def require_evidence_pilot():
    if not get_settings().cold_start_evidence_enabled:
        raise HTTPException(404, "Not found")


Actor = Annotated[User, Depends(get_current_user)]
Database = Annotated[Session, Depends(get_db)]
Clock = Annotated[datetime, Depends(get_now)]

router = APIRouter(tags=["pilot-evidence"], dependencies=[Depends(require_evidence_pilot)])


def owner_app(db: Session, app_id: str, actor: User) -> App:
    app = db.get(App, app_id)
    if app is None or app.owner_id != actor.id:
        raise HTTPException(404, "App not found")
    return app


def access_mission(db: Session, mission_id: str, actor: User) -> TestMission:
    mission = db.get(TestMission, mission_id)
    if mission is None or actor.id not in {
        mission.assignment.tester_id,
        mission.assignment.app.owner_id,
    }:
        raise HTTPException(404, "Mission not found")
    return mission


def find_run(db: Session, run_id: str, actor: User) -> tuple[MissionRun, TestMission]:
    run = db.scalar(select(MissionRun).where(MissionRun.id == run_id))
    if run is None:
        raise HTTPException(404, "Run not found")
    return run, access_mission(db, run.mission_id, actor)


@router.post(
    "/assignments/{assignment_id}/enrollment-evidence",
    response_model=EnrollmentEvidenceRead,
    status_code=201,
)
def record_enrollment(
    assignment_id: str,
    body: EnrollmentEvidenceCreate,
    actor: Actor,
    db: Database,
    now: Clock,
):
    assignment = db.get(TesterAssignment, assignment_id)
    if assignment is None or actor.id not in {assignment.tester_id, assignment.app.owner_id}:
        raise HTTPException(404, "Assignment not found")
    expected_actor = (
        assignment.tester_id if body.source == "SELF_REPORTED" else assignment.app.owner_id
    )
    if actor.id != expected_actor:
        raise HTTPException(403, "Evidence source does not match the recording actor")
    if body.event == "JOINED" and assignment.status == "DROPPED":
        raise HTTPException(409, "Create a new assignment before rejoining")
    row = EnrollmentEvidence(
        assignment_id=assignment_id,
        recorded_by_id=actor.id,
        recorded_at=now,
        **body.model_dump(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/apps/{app_id}/evidence/build")
def set_candidate_build(
    app_id: str,
    body: MissionRunFixCreate,
    actor: Actor,
    db: Database,
    now: Clock,
):
    owner_app(db, app_id, actor)
    row = db.get(CampaignBuild, app_id)
    if row is None:
        row = CampaignBuild(app_id=app_id)
        db.add(row)
    row.version_code = body.target_version_code
    row.recorded_by_id = actor.id
    row.recorded_at = now
    db.commit()
    return {"app_id": app_id, "target_version_code": row.version_code}


@router.get("/missions/{mission_id}/evidence-context")
def evidence_context(
    mission_id: str,
    actor: Actor,
    db: Database,
):
    mission = access_mission(db, mission_id, actor)
    app = mission.assignment.app
    build = db.get(CampaignBuild, app.id)
    goal, steps = mission_instructions(mission.mission_type, app.name, app.core_workflow_steps)
    return {
        "mission_id": mission.id,
        "assignment_id": mission.assignment_id,
        "package_name": app.package_name,
        "expected_version_code": build.version_code if build else None,
        "assignment_status": mission.assignment.status,
        "goal": goal,
        "steps": steps,
    }


@router.post("/missions/{mission_id}/runs", response_model=MissionRunRead, status_code=201)
def submit_run(
    mission_id: str,
    body: MissionRunCreate,
    actor: Actor,
    db: Database,
    now: Clock,
):
    mission = access_mission(db, mission_id, actor)
    payload = body.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def replay():
        existing = db.scalar(
            select(MissionRun).where(
                MissionRun.mission_id == mission_id,
                MissionRun.idempotency_key == body.idempotency_key,
            )
        )
        if existing is not None and (
            existing.submitted_by_id != actor.id or existing.payload_hash != digest
        ):
            raise HTTPException(409, "Idempotency key is already used by another submission")
        return existing

    existing = replay()
    if existing is not None:
        return existing
    assignment = mission.assignment
    refresh_mission_availability(db, [mission], now)
    if body.result in {"PASS", "FAIL"} and mission.status not in {"AVAILABLE", "COMPLETED"}:
        raise HTTPException(409, "Mission is not available for execution")
    if assignment.status == "DROPPED":
        raise HTTPException(409, "Cannot submit new runs for a dropped assignment")
    if body.execution_source == "HUMAN_MANUAL" and actor.id != assignment.tester_id:
        raise HTTPException(403, "Only the assigned tester can submit manual tester evidence")
    if body.result in {"PASS", "FAIL"} and assignment.installed_at is None:
        raise HTTPException(409, "Confirm installation before recording executed steps")
    if body.package_name != assignment.app.package_name:
        raise HTTPException(409, "Evidence package does not match this app")
    build = db.get(CampaignBuild, assignment.app_id)
    if build is None or body.expected_version_code != build.version_code:
        raise HTTPException(409, "Owner must confirm the current candidate build")
    if body.version_code != build.version_code and body.result != "BLOCKED":
        raise HTTPException(409, "Wrong build must be recorded as BLOCKED")
    _, required_steps = mission_instructions(
        mission.mission_type, assignment.app.name, assignment.app.core_workflow_steps
    )
    if body.result == "PASS" and [step.instruction for step in body.steps] != required_steps:
        raise HTTPException(409, "PASS requires evidence for every assigned mission step")
    if body.retest_of_id:
        parent, parent_mission = find_run(db, body.retest_of_id, actor)
        fix = db.scalar(select(MissionRunFix).where(MissionRunFix.run_id == parent.id))
        if (
            parent_mission.assignment.app_id != assignment.app_id
            or parent.result != "FAIL"
            or fix is None
            or body.version_code != fix.target_version_code
        ):
            raise HTTPException(409, "Retest requires a failure and its declared fixed build")
        if [step.instruction for step in body.steps] != [
            step["instruction"] for step in parent.details["steps"]
        ]:
            raise HTTPException(409, "Retest must repeat the original failing run steps")
    row = MissionRun(
        mission_id=mission.id,
        submitted_by_id=actor.id,
        idempotency_key=body.idempotency_key,
        payload_hash=digest,
        execution_source=body.execution_source,
        result=body.result,
        package_name=body.package_name,
        version_code=body.version_code,
        device_key=body.device_key,
        device_model=body.device_model,
        android_api=body.android_api,
        retest_of_id=body.retest_of_id,
        recorded_at=now,
        details={
            "steps": payload["steps"],
            "note": body.note,
            "expected_version_code": body.expected_version_code,
        },
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = replay()
        if existing is not None:
            return existing
        raise HTTPException(409, "Submission conflict; retry the original request") from None
    db.refresh(row)
    return row


@router.get("/missions/{mission_id}/runs", response_model=list[MissionRunRead])
def mission_runs(
    mission_id: str,
    actor: Actor,
    db: Database,
):
    access_mission(db, mission_id, actor)
    return list(
        db.scalars(
            select(MissionRun)
            .where(MissionRun.mission_id == mission_id)
            .order_by(MissionRun.sequence)
        )
    )


@router.post("/runs/{run_id}/fix")
def record_fix(
    run_id: str,
    body: MissionRunFixCreate,
    actor: Actor,
    db: Database,
    now: Clock,
):
    row, mission = find_run(db, run_id, actor)
    owner_app(db, mission.assignment.app_id, actor)
    if row.result != "FAIL":
        raise HTTPException(409, "Only failing runs can have a fix declaration")
    fix = db.scalar(select(MissionRunFix).where(MissionRunFix.run_id == run_id))
    if fix is not None:
        if (
            fix.target_version_code != body.target_version_code
            or fix.description != body.description
        ):
            raise HTTPException(409, "Fix declaration exists; record a new failure for another fix")
    else:
        fix = MissionRunFix(
            run_id=run_id, recorded_by_id=actor.id, recorded_at=now, **body.model_dump()
        )
        db.add(fix)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Fix declaration conflict; reload before retrying") from None
    return {
        "run_id": run_id,
        "target_version_code": fix.target_version_code,
        "state": "READY_FOR_RETEST",
        "verified_fixed": False,
    }


@router.get("/apps/{app_id}/evidence-summary")
def evidence_summary(
    app_id: str,
    actor: Actor,
    db: Database,
    now: Clock,
):
    app = owner_app(db, app_id, actor)
    assignments = list(
        db.scalars(select(TesterAssignment).where(TesterAssignment.app_id == app_id))
    )
    assignment_ids = [item.id for item in assignments]
    by_id = {item.id: item for item in assignments}
    events = list(
        db.scalars(
            select(EnrollmentEvidence)
            .where(EnrollmentEvidence.assignment_id.in_(assignment_ids))
            .order_by(EnrollmentEvidence.sequence)
        )
    )
    states: dict[str, dict] = {}
    for event in events:
        assignment = by_id[event.assignment_id]
        previous = states.get(assignment.tester_id)
        start = None
        if event.event == "JOINED":
            start = (
                previous["start"]
                if previous
                and previous["event"] == "JOINED"
                and by_id[previous["assignment_id"]].status != "DROPPED"
                else event.recorded_at
            )
        states[assignment.tester_id] = {
            "event": event.event,
            "start": start,
            "source": event.source,
            "assignment_id": event.assignment_id,
        }
    active = [
        state
        for state in states.values()
        if state["event"] == "JOINED" and by_id[state["assignment_id"]].status != "DROPPED"
    ]
    starts = sorted(aware(state["start"]) for state in active)
    runs = list(
        db.scalars(
            select(MissionRun)
            .join(TestMission)
            .join(TesterAssignment)
            .where(TesterAssignment.app_id == app_id)
            .order_by(MissionRun.sequence)
        )
    )
    build = db.get(CampaignBuild, app.id)
    current_runs = [run for run in runs if build and run.version_code == build.version_code]
    latest = {}
    for run in current_runs:
        latest[(run.mission_id, run.device_key)] = run
    issues = []
    for failure in [run for run in runs if run.result == "FAIL"]:
        fix = db.scalar(select(MissionRunFix).where(MissionRunFix.run_id == failure.id))
        retests = [run for run in runs if run.retest_of_id == failure.id]
        successful = bool(
            fix
            and retests
            and retests[-1].result == "PASS"
            and retests[-1].version_code == fix.target_version_code
        )
        issues.append(
            {
                "run_id": failure.id,
                "reported_version_code": failure.version_code,
                "fixed_version_code": fix.target_version_code if fix else None,
                "state": (
                    "VERIFIED_FIXED"
                    if successful
                    else "STILL_REPRODUCIBLE"
                    if retests and retests[-1].result == "FAIL"
                    else "READY_FOR_RETEST"
                    if fix
                    else "REPORTED"
                ),
                "last_retest_result": retests[-1].result if retests else None,
            }
        )
    counts = {
        result: sum(run.result == result for run in latest.values())
        for result in ("PASS", "FAIL", "BLOCKED", "NOT_RUN")
    }
    legacy_completed = (
        db.scalar(
            select(func.count(TestMission.id))
            .join(TesterAssignment)
            .where(TesterAssignment.app_id == app_id, TestMission.status == "COMPLETED")
        )
        or 0
    )
    return {
        "app_id": app_id,
        "package_name": app.package_name,
        "candidate_version_code": build.version_code if build else None,
        "assigned_participants": len({item.tester_id for item in assignments}),
        "reported_joined_participants": len(active),
        "owner_confirmed_joined_participants": sum(
            state["source"] == "OWNER_CONFIRMED" for state in active
        ),
        "reported_continuous_14_days": sum(
            start + timedelta(days=14) <= aware(now) for start in starts
        ),
        "estimated_eligibility_at": (starts[11] + timedelta(days=14)).isoformat()
        if len(starts) >= 12
        else None,
        "eligibility_estimate_only": True,
        "google_eligibility_confirmed": False,
        "enrollment_verification_source": "APP_RECORDED_EVIDENCE_NOT_GOOGLE_SYNC",
        "manual_reported_participants": len(
            {run.submitted_by_id for run in runs if run.execution_source == "HUMAN_MANUAL"}
        ),
        "total_runs": len(runs),
        "current_build_results": counts,
        "current_build_device_coverage": len(
            {run.device_key for run in current_runs if run.result in {"PASS", "FAIL"}}
        ),
        "execution_sources": {
            source: sum(run.execution_source == source for run in runs)
            for source in ("HUMAN_MANUAL", "CODEX_ASSISTED", "AUTOMATED_RUNNER")
        },
        "legacy_completed_missions_without_run_evidence": legacy_completed
        - sum(
            mission_id in {run.mission_id for run in runs}
            for mission_id in db.scalars(
                select(TestMission.id)
                .join(TesterAssignment)
                .where(TesterAssignment.app_id == app_id, TestMission.status == "COMPLETED")
            )
        ),
        "issues": issues,
        "internal_readiness": "REVIEW_REQUIRED",
        "limitations": [
            "Recorded enrollment is not proof of current Google opt-in or actual tester identity.",
            "Runner results do not become manual feedback or increase tester counts.",
            "Build-scoped coverage and owner fix declarations do not guarantee approval.",
        ],
    }


@router.get("/assignments/{assignment_id}/evidence-status")
def evidence_assignment_status(assignment_id: str, actor: Actor, db: Database):
    assignment = db.get(TesterAssignment, assignment_id)
    if assignment is None or actor.id not in {assignment.tester_id, assignment.app.owner_id}:
        raise HTTPException(404, "Assignment not found")
    return {"assignment_id": assignment.id, "assignment_status": assignment.status}


@router.get("/apps/{app_id}/evidence-report")
def evidence_report(app_id: str, actor: Actor, db: Database, now: Clock):
    summary = evidence_summary(app_id, actor, db, now)
    rows = list(
        db.scalars(
            select(MissionRun)
            .join(TestMission)
            .join(TesterAssignment)
            .where(TesterAssignment.app_id == app_id)
            .order_by(MissionRun.sequence)
        )
    )
    return {
        "title": "Pilot testing evidence report",
        "generated_at": aware(now).isoformat(),
        "summary": summary,
        "runs": [MissionRunRead.model_validate(row).model_dump(mode="json") for row in rows],
    }
