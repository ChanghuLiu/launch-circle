"""Local operator review. No public approval endpoint or automatic identity grant."""

import re
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.launch import App, DeveloperAccount
from app.models.pool import AppIntake
from app.models.user import User
from app.services.circles import ensure_owner_circle


def approve_intake(
    db: Session, request_id: str, *, reviewer: str, proof_sha256: str, note: str, now: datetime
) -> AppIntake:
    if not reviewer.strip() or len(reviewer) > 100 or not 10 <= len(note.strip()) <= 500:
        raise ValueError("Provide reviewer and a concise ownership-review note")
    if not re.fullmatch(r"[a-f0-9]{64}", proof_sha256):
        raise ValueError("An ownership evidence hash is required")
    # SQLite writer lock before entitlement and package checks.
    db.execute(update(AppIntake).where(AppIntake.id == request_id).values(status=AppIntake.status))
    row = db.get(AppIntake, request_id)
    if row is None:
        raise ValueError("Request not found")
    if row.status == "APPROVED":
        return row
    if row.status != "PENDING":
        raise ValueError("Request is not pending")
    owner = db.get(User, row.owner_id)
    if owner is None or not owner.is_active:
        raise ValueError("Owner is unavailable")
    if db.scalar(select(App.id).where(App.package_name == row.package_name)):
        raise ValueError("Package is already registered")
    account = db.scalar(
        select(DeveloperAccount).where(
            DeveloperAccount.play_developer_account_id == row.developer_account_id
        )
    )
    if account is not None and (
        account.first_free_claimed_at is not None
        or db.scalar(select(App.id).where(App.developer_account_id == account.id).limit(1))
    ):
        raise ValueError("Publisher first-app entitlement is already used; do not bypass Billing")
    if account is None:
        account = DeveloperAccount(
            play_developer_account_id=row.developer_account_id,
            identity_method="USER_PROVIDED",
            verification_status="UNVERIFIED",
        )
        db.add(account)
        db.flush()
    # Manual package authorization is not Google attestation of the claimed
    # numeric account identity and never grants publisher-unlimited access.
    circle = ensure_owner_circle(db, owner)
    item = App(
        owner_id=owner.id,
        developer_account_id=account.id,
        circle_id=circle.id,
        entitlement_status="FIRST_APP_FREE",
        name=row.name,
        package_name=row.package_name,
        opt_in_url="https://play.google.com/apps/testing/" + row.package_name,
        core_workflow_steps=row.workflow_steps,
        tester_target=14,
        status="WAITING_FOR_TESTERS",
        google_group_configured=False,
    )
    db.add(item)
    db.flush()
    account.first_free_claimed_at = now
    row.status, row.app_id, row.reviewed_at = "APPROVED", item.id, now
    row.reviewer, row.proof_sha256, row.review_note = reviewer.strip(), proof_sha256, note.strip()
    return row
