from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_google_id_token,
)
from app.models.user import User
from app.schemas.auth import GoogleAuthRequest, LogoutRequest, RefreshRequest, TokenPair

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/google", response_model=TokenPair)
def google_auth(body: GoogleAuthRequest, db: Session = Depends(get_db)) -> TokenPair:
    payload = verify_google_id_token(body.id_token)
    user = db.scalar(
        select(User).where(
            or_(
                User.google_subject == payload["sub"],
                User.email == payload["email"].lower(),
            )
        )
    )
    if user is None:
        user = User(
            google_subject=payload["sub"],
            email=payload["email"].lower(),
            login_email=payload["email"],
            display_name=payload.get("name"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.google_subject = payload["sub"]
        user.email = payload["email"].lower()
        user.login_email = payload["email"]
        if payload.get("name") and not user.display_name:
            user.display_name = payload["name"]
        db.commit()

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(db, user.id),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    access, refresh_token = rotate_refresh_token(db, body.refresh_token)
    return TokenPair(access_token=access, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
def logout(body: LogoutRequest, db: Session = Depends(get_db)) -> None:
    revoke_refresh_token(db, body.refresh_token)
