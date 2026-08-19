from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.device import Device
from app.models.user import User
from app.schemas.user import DeviceUpdate, TesterEmailUpdate, UserRead, UserUpdate

router = APIRouter(prefix="/v1/me", tags=["me"])


def serialize_user(user: User) -> UserRead:
    languages = [item for item in user.languages_csv.split(",") if item]
    profile_ready = bool(
        user.tester_email
        and user.tester_email_sharing_consent
        and user.country
        and languages
    )
    return UserRead(
        id=user.id,
        login_email=user.login_email,
        display_name=user.display_name,
        tester_email=user.tester_email,
        tester_email_sharing_consent=user.tester_email_sharing_consent,
        country=user.country,
        languages=languages,
        profile_ready=profile_ready,
    )


@router.get("", response_model=UserRead)
def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return serialize_user(current_user)


@router.put("", response_model=UserRead)
def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    values = body.model_dump(exclude_unset=True)
    if "display_name" in values:
        current_user.display_name = values["display_name"]
    if "country" in values:
        current_user.country = values["country"]
    if "languages" in values:
        current_user.languages_csv = ",".join(values["languages"] or [])
    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user)


@router.put("/tester-email", response_model=UserRead)
def update_tester_email(
    body: TesterEmailUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    if not body.sharing_consent:
        raise HTTPException(status_code=422, detail="Sharing consent is required")
    current_user.tester_email = str(body.tester_email)
    current_user.tester_email_sharing_consent = True
    current_user.tester_email_sharing_consent_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user)


@router.put("/device")
def update_device(
    body: DeviceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    device = db.scalar(select(Device).where(Device.installation_id == body.installation_id))
    if device is not None and device.user_id != current_user.id:
        raise HTTPException(status_code=409, detail="Installation belongs to another user")
    if device is None:
        device = Device(user_id=current_user.id, installation_id=body.installation_id)
        db.add(device)
    device.manufacturer = body.manufacturer
    device.model = body.model
    device.android_api = body.android_api
    device.capabilities_csv = ",".join(body.capabilities)
    device.last_seen_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(device)
    return {
        "id": device.id,
        "installation_id": device.installation_id,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "android_api": device.android_api,
        "capabilities": [item for item in device.capabilities_csv.split(",") if item],
    }
