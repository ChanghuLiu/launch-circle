"""Persist explicit App Group consent for legacy assignment scenarios.

These integration tests focus on assignment/lifecycle behavior, not the join
endpoint itself. The dedicated App Group and authorization tests exercise that
endpoint and its denial paths. This helper seeds the equivalent valid persisted
state, including one app per consenting owner in the target app's matched group.
"""
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.launch import App
from app.models.pool import AppGroup, AppGroupApp, AppGroupMember, PoolListing


def seed_app_group_consent(app_id: str, user_ids: list[str]) -> None:
    """Model users who own an app in, and have joined, the target app's group."""
    stamp = datetime.now(UTC)
    with SessionLocal() as db:
        target = db.get(App, app_id)
        if target is None:
            raise AssertionError(f"fixture target App {app_id} does not exist")
        target_mapping = db.get(AppGroupApp, app_id)
        if target_mapping is None:
            group_id = str(uuid4())
            db.add(AppGroup(id=group_id, name="Explicit consent fixture group", created_at=stamp))
            db.flush()
            db.add(AppGroupApp(app_id=target.id, group_id=group_id))
            db.flush()
        else:
            group_id = target_mapping.group_id

        listing = db.get(PoolListing, target.id)
        if listing is None:
            db.add(PoolListing(app_id=target.id, enabled=True, updated_at=stamp))
        else:
            listing.enabled = True
            listing.updated_at = stamp

        occupied = db.scalar(
            select(func.count(AppGroupApp.app_id)).where(AppGroupApp.group_id == group_id)
        ) or 0
        group_owners = set(db.scalars(
            select(App.owner_id)
            .join(AppGroupApp, AppGroupApp.app_id == App.id)
            .where(AppGroupApp.group_id == group_id)
        ))

        for user_id in dict.fromkeys(user_ids):
            if user_id == target.owner_id:
                continue
            if db.get(AppGroupMember, (group_id, user_id)) is not None:
                continue
            if user_id not in group_owners:
                if occupied >= 15:
                    raise AssertionError("fixture exceeds the 15-app App Group capacity")
                package = "com.fixture.group." + uuid4().hex
                member_app = App(
                    owner_id=user_id,
                    name="Consent fixture App",
                    package_name=package,
                    opt_in_url=f"https://play.google.com/apps/testing/{package}",
                    icon_url="https://example.invalid/fixture.png",
                    google_group_configured=True,
                )
                db.add(member_app)
                db.flush()
                db.add(AppGroupApp(app_id=member_app.id, group_id=group_id))
                occupied += 1
                group_owners.add(user_id)
            db.add(AppGroupMember(group_id=group_id, user_id=user_id, joined_at=stamp))
        db.commit()


def seed_circle_app_group_consent(app_id: str) -> None:
    """Seed all active Circle members as explicit members of the matched group."""
    from app.models.launch import CircleMember

    with SessionLocal() as db:
        target = db.get(App, app_id)
        if target is None or target.circle_id is None:
            raise AssertionError(f"fixture target App {app_id} has no Circle")
        user_ids = list(db.scalars(
            select(CircleMember.user_id).where(
                CircleMember.circle_id == target.circle_id,
                CircleMember.status == "ACTIVE",
                CircleMember.user_id != target.owner_id,
            ).order_by(CircleMember.joined_at, CircleMember.user_id)
        ))
    seed_app_group_consent(app_id, user_ids)
