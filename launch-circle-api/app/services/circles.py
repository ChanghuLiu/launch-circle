from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.launch import Circle, CircleMember
from app.models.user import User

CIRCLE_MAX_MEMBERS = 15


def circle_name(user: User) -> str:
    display_name = (user.display_name or "Developer").strip()
    return f"{display_name}'s Launch Circle"


def ensure_owner_circle(db: Session, user: User) -> Circle:
    """Return the user's durable home circle, creating its owner membership if needed."""
    circle = db.scalar(select(Circle).where(Circle.owner_id == user.id))
    if circle is None:
        circle = Circle(owner_id=user.id, name=circle_name(user), max_members=CIRCLE_MAX_MEMBERS)
        db.add(circle)
        db.flush()
    owner_member = db.scalar(
        select(CircleMember).where(
            CircleMember.circle_id == circle.id,
            CircleMember.user_id == user.id,
        )
    )
    if owner_member is None:
        db.add(
            CircleMember(
                circle_id=circle.id,
                user_id=user.id,
                role="OWNER",
                status="ACTIVE",
            )
        )
    elif owner_member.status != "ACTIVE" or owner_member.role != "OWNER":
        owner_member.status = "ACTIVE"
        owner_member.role = "OWNER"
        owner_member.left_at = None
    db.flush()
    return circle


def active_member(db: Session, circle_id: str, user_id: str) -> CircleMember | None:
    return db.scalar(
        select(CircleMember).where(
            CircleMember.circle_id == circle_id,
            CircleMember.user_id == user_id,
            CircleMember.status == "ACTIVE",
        )
    )


def active_member_count(db: Session, circle_id: str) -> int:
    return int(
        db.scalar(
            select(func.count(CircleMember.id)).where(
                CircleMember.circle_id == circle_id,
                CircleMember.status == "ACTIVE",
            )
        )
        or 0
    )
