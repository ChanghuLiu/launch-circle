from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_google_id_token,
)
from app.models.user import User
from app.schemas.auth import GoogleAuthRequest, LogoutRequest, RefreshRequest, TokenPair
from app.services.circles import ensure_owner_circle

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/google", response_model=TokenPair)
def google_auth(body: GoogleAuthRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    payload = verify_google_id_token(body.id_token)
    user = db.scalar(
        select(User).where(
            or_(
                User.google_subject == payload["sub"],
                User.email == payload["email"].lower(),
            )
        )
    )
    registered = user is None
    if user is None:
        user = User(
            google_subject=payload["sub"],
            email=payload["email"].lower(),
            login_email=payload["email"],
            display_name=payload.get("name"),
            acquisition_source=body.acquisition_source or "UNKNOWN",
            acquisition_medium=body.acquisition_medium,
            acquisition_campaign=body.acquisition_campaign,
            attribution_captured_at=(datetime.now(timezone.utc) if body.acquisition_source else None),
        )
        db.add(user)
        db.flush()
        ensure_owner_circle(db, user)
        db.commit()
        db.refresh(user)
    else:
        user.google_subject = payload["sub"]
        user.email = payload["email"].lower()
        user.login_email = payload["email"]
        if payload.get("name") and not user.display_name:
            user.display_name = payload["name"]
        if user.acquisition_source == "UNKNOWN" and body.acquisition_source:
            user.acquisition_source = body.acquisition_source
            user.acquisition_medium = body.acquisition_medium
            user.acquisition_campaign = body.acquisition_campaign
            user.attribution_captured_at = datetime.now(timezone.utc)
        ensure_owner_circle(db, user)
        db.commit()

    request.state.activity_user_id = user.id
    request.state.activity_event = ("auth.register" if registered else "auth.sign_in", "auth")
    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(db, user.id),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, request: Request, db: Session = Depends(get_db)) -> TokenPair:
    access, refresh_token = rotate_refresh_token(db, body.refresh_token)
    try:
        request.state.activity_user_id = jwt.decode(
            access, get_settings().jwt_secret, algorithms=[get_settings().jwt_algorithm]
        ).get("sub")
    except jwt.PyJWTError:
        pass
    request.state.activity_event = ("auth.session_refresh", "auth")
    return TokenPair(access_token=access, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
def logout(body: LogoutRequest, request: Request, db: Session = Depends(get_db)) -> None:
    from app.core.security import hash_refresh_token
    from app.models.refresh_token import RefreshToken

    token = db.scalar(select(RefreshToken).where(
        RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
    ))
    revoke_refresh_token(db, body.refresh_token)
    if token is not None:
        request.state.activity_user_id = token.user_id
    request.state.activity_event = ("auth.sign_out", "auth")
