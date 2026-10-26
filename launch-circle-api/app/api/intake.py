"""Private assisted onboarding. Submission never verifies ownership or creates an app."""

from datetime import datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.pool import Actor, Clock, Database, lock_writes
from app.models.launch import App
from app.models.pool import AppIntake

router = APIRouter(tags=["assisted-onboarding"])


class IntakeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    package_name: str = Field(
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$", max_length=255
    )
    developer_account_id: str = Field(pattern=r"^[0-9]{8,64}$")
    workflow_steps: Annotated[
        list[Annotated[str, Field(min_length=1, max_length=400)]], Field(min_length=1, max_length=5)
    ]


class IntakeRead(BaseModel):
    id: str
    name: str
    package_name: str
    status: str
    app_id: str | None
    submitted_at: datetime


def read(row: AppIntake):
    return IntakeRead(
        id=row.id,
        name=row.name,
        package_name=row.package_name,
        status=row.status,
        app_id=row.app_id,
        submitted_at=row.submitted_at,
    )


@router.get("/app-intakes", response_model=list[IntakeRead])
def my_intakes(actor: Actor, db: Database):
    rows = db.scalars(
        select(AppIntake)
        .where(AppIntake.owner_id == actor.id)
        .order_by(AppIntake.submitted_at.desc())
        .limit(100)
    )
    return [read(row) for row in rows]


@router.post("/app-intakes", response_model=IntakeRead)
def submit_intake(body: IntakeCreate, actor: Actor, db: Database, now: Clock):
    lock_writes(db, actor)
    if not body.name.strip() or any(not step.strip() for step in body.workflow_steps):
        raise HTTPException(422, "Provide a name and meaningful workflow steps")
    existing = db.scalar(
        select(AppIntake).where(
            AppIntake.owner_id == actor.id, AppIntake.package_name == body.package_name
        )
    )
    if existing:
        return read(existing)
    if db.scalar(select(App.id).where(App.package_name == body.package_name)):
        raise HTTPException(409, "This package is already registered")
    pending = (
        db.scalar(
            select(func.count(AppIntake.id)).where(
                AppIntake.owner_id == actor.id, AppIntake.status == "PENDING"
            )
        )
        or 0
    )
    if pending >= 2:
        raise HTTPException(409, "Two onboarding requests are already awaiting review")
    row = AppIntake(
        id=str(uuid4()),
        owner_id=actor.id,
        name=body.name.strip(),
        package_name=body.package_name,
        developer_account_id=body.developer_account_id,
        workflow_steps=[step.strip() for step in body.workflow_steps],
        submitted_at=now,
        status="PENDING",
    )
    db.add(row)
    db.commit()
    return read(row)
