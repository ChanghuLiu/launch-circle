from app.core.database import SessionLocal
from app.models.launch import App
from app.models.pool import PoolListing, AppGroupMember
from sqlalchemy import select
from tests.test_shared_pool import actor, campaign, post
from tests.test_admin import operator, HEADERS


def test_setup_shows_on_home_without_opening_recruitment(client):
    owner, tester = actor(), actor()
    aid = campaign(owner)
    with SessionLocal() as db:
        db.get(App, aid).google_group_configured = False
        db.commit()
    assert not client.get("/tester-pool/apps", headers=tester[1]).json()
    assert post(client, f"/apps/{aid}/google-group/confirm", owner, {"configured": True}).status_code == 200
    rows = client.get("/tester-pool/apps", headers=tester[1]).json()
    assert rows[0]["app_id"] == aid and not rows[0]["available"]
    with SessionLocal() as db:
        assert db.get(PoolListing, aid) is None
        assert db.scalar(select(AppGroupMember)) is None
    assert post(client, f"/apps/{aid}/pool-listing", owner, {"enabled": True, "reason": "Owner completed app setup"}).status_code == 403


def test_only_operator_opens_recruitment_and_pause_does_not_hide_app(operator):
    owner, tester = actor(), actor()
    aid = campaign(owner)
    path = f"/admin/api/apps/{aid}/recruitment"
    assert operator.post(path, json={"enabled": True, "reason": "Owner completed app setup"}, headers=HEADERS).status_code == 200
    rows = operator.get("/tester-pool/apps", headers=tester[1]).json()
    assert rows[0]["available"]
    with SessionLocal() as db:
        assert db.scalar(select(AppGroupMember)) is None
    assert operator.post(path, json={"enabled": False, "reason": "Pause while owner reviews setup"}, headers=HEADERS).status_code == 200
    rows = operator.get("/tester-pool/apps", headers=tester[1]).json()
    assert rows[0]["app_id"] == aid and not rows[0]["available"]


def test_regular_user_cannot_use_operator_recruitment(client):
    owner = actor()
    aid = campaign(owner)
    assert client.post(f"/admin/api/apps/{aid}/recruitment", json={"enabled": True, "reason": "Owner completed app setup"}, headers={**owner[1], **HEADERS}).status_code == 401


def test_missing_icon_stays_in_my_launch_and_cannot_recruit(operator):
    owner, tester = actor(), actor()
    aid = campaign(owner)
    with SessionLocal() as db:
        db.get(App, aid).icon_url = None
        db.commit()
    assert not operator.get("/tester-pool/apps", headers=tester[1]).json()
    assert operator.get(f"/apps/{aid}", headers=owner[1]).status_code == 200
    assert operator.post(f"/admin/api/apps/{aid}/recruitment", json={"enabled": True, "reason": "Owner completed app setup"}, headers=HEADERS).status_code == 409
