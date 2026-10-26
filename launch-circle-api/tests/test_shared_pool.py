from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.models.launch import App, CircleMember, TesterAssignment
from app.models.pool import PoolListing, TesterPoolPreference
from app.models.user import User
from app.services.circles import ensure_owner_circle

NOW = datetime.now(UTC)


def actor():
    with SessionLocal() as db:
        uid = str(uuid4())
        user = User(id=uid, email=uid + "@example.com", login_email=uid + "@example.com")
        db.add(user)
        db.commit()
    return uid, {"Authorization": "Bearer " + create_access_token(uid)}


def campaign(owner):
    with SessionLocal() as db:
        circle = ensure_owner_circle(db, db.get(User, owner[0]))
        item = App(
            owner_id=owner[0],
            circle_id=circle.id,
            name="Test App",
            package_name="com.example.a" + uuid4().hex,
            opt_in_url="placeholder",
            google_group_configured=True,
            core_workflow_steps=["Open app", "Complete main action"],
        )
        db.add(item)
        db.flush()
        item.opt_in_url = "https://play.google.com/apps/testing/" + item.package_name
        aid = item.id
        db.commit()
        return aid


def post(client, path, who, body=None):
    return client.post(path, headers=who[1], json=body)


def open_app(client, aid, owner):
    res = post(client, "/apps/" + aid + "/pool-listing", owner, {"enabled": True})
    assert res.status_code == 200, res.text


@pytest.mark.parametrize("customers", range(1, 13))
def test_one_through_twelve_customers_have_separate_consent_and_bounded_work(client, customers):
    apps = []
    for _ in range(customers):
        owner = actor()
        aid = campaign(owner)
        open_app(client, aid, owner)
        apps.append((aid, owner))
    # Fourteen volunteers per pair of apps. Twelve parallel apps require
    # 84 volunteers at the two-app cap, not fourteen overloaded people.
    for first in range(0, customers, 2):
        for _ in range(14):
            tester = actor()
            assert post(client, "/tester-pool/me", tester, {"enabled": True}).status_code == 200
            for aid, _owner in apps[first : first + 2]:
                res = post(client, "/apps/" + aid + "/tester-pool/accept", tester)
                assert res.status_code == 200, res.text
                replay = post(client, "/apps/" + aid + "/tester-pool/accept", tester)
                assert replay.json() == res.json()
    for aid, owner in apps:
        data = client.get("/apps/" + aid + "/supply", headers=owner[1]).json()
        assert data["accepted_participants"] == 14
        assert data["reported_joined_and_installed"] == 0
        assert data["missing_to_minimum"] == 12
        assert data["google_eligibility_confirmed"] is False
    with SessionLocal() as db:
        assert db.scalar(select(func.count(TesterAssignment.id))) == customers * 14
        assert all(
            a.opted_in_at is None and a.installed_at is None
            for a in db.scalars(select(TesterAssignment))
        )


def test_consent_ownership_revocation_and_no_implicit_assignment(client):
    owner, tester, stranger = actor(), actor(), actor()
    aids = [campaign(owner) for _ in range(3)]
    for aid in aids:
        open_app(client, aid, owner)
    assert client.get("/tester-pool/opportunities", headers=tester[1]).json() == []
    assert post(client, "/apps/" + aids[0] + "/tester-pool/accept", tester).status_code == 409
    assert (
        post(client, "/apps/" + aids[0] + "/pool-listing", stranger, {"enabled": False}).status_code
        == 404
    )
    assert client.get("/apps/" + aids[0] + "/supply", headers=stranger[1]).status_code == 404
    post(client, "/tester-pool/me", tester, {"enabled": True})
    found = client.get("/tester-pool/opportunities", headers=tester[1]).json()
    assert len(found) == 3
    assert "email" not in str(found) and "opt_in_url" not in str(found)
    for aid in aids[:2]:
        assert post(client, "/apps/" + aid + "/tester-pool/accept", tester).status_code == 200
    assert post(client, "/apps/" + aids[2] + "/tester-pool/accept", tester).status_code == 409
    assert client.get("/tester-pool/opportunities", headers=tester[1]).json() == []
    # Circle membership gained from one app must not imply consent to another.
    matched = post(client, "/apps/" + aids[2] + "/match-testers", owner)
    assert matched.status_code == 200, matched.text
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count(TesterAssignment.id)).where(TesterAssignment.app_id == aids[2])
            )
            == 0
        )
    post(client, "/tester-pool/me", tester, {"enabled": False})
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count(TesterAssignment.id)).where(
                    TesterAssignment.tester_id == tester[0]
                )
            )
            == 2
        )
    assert post(client, "/apps/" + aids[0] + "/tester-pool/accept", tester).status_code == 409
    # Deletion cascades preferences and owned listings.
    assert client.delete("/v1/me", headers=tester[1]).status_code == 200
    with SessionLocal() as db:
        assert db.get(TesterPoolPreference, tester[0]) is None
    assert client.delete("/v1/me", headers=owner[1]).status_code == 200
    with SessionLocal() as db:
        assert db.get(PoolListing, aids[0]) is None


def test_capacity_closed_listing_and_unready_campaign(client):
    owner = actor()
    aid = campaign(owner)
    with SessionLocal() as db:
        item = db.get(App, aid)
        item.google_group_configured = False
        db.commit()
    assert (
        post(client, "/apps/" + aid + "/pool-listing", owner, {"enabled": True}).status_code == 409
    )
    with SessionLocal() as db:
        item = db.get(App, aid)
        item.google_group_configured = True
        db.commit()
    open_app(client, aid, owner)
    with SessionLocal() as db:
        circle_id = db.get(App, aid).circle_id
        for _ in range(14):
            uid = str(uuid4())
            db.add(User(id=uid, email=uid + "@example.com", login_email=uid + "@example.com"))
            db.flush()
            db.add(
                CircleMember(
                    circle_id=circle_id, user_id=uid, role="MEMBER", status="ACTIVE", joined_at=NOW
                )
            )
        db.commit()
    tester = actor()
    post(client, "/tester-pool/me", tester, {"enabled": True})
    assert post(client, "/apps/" + aid + "/tester-pool/accept", tester).status_code == 409
    post(client, "/apps/" + aid + "/pool-listing", owner, {"enabled": False})
    assert post(client, "/apps/" + aid + "/tester-pool/accept", tester).status_code == 404
    assert client.get("/tester-pool/me").status_code == 401


def test_concurrent_acceptance_enforces_two_app_quota(client):
    from concurrent.futures import ThreadPoolExecutor

    owner, tester = actor(), actor()
    aids = [campaign(owner) for _ in range(3)]
    for aid in aids:
        open_app(client, aid, owner)
    post(client, "/tester-pool/me", tester, {"enabled": True})
    with ThreadPoolExecutor(max_workers=3) as workers:
        statuses = list(
            workers.map(
                lambda aid: (
                    post(client, "/apps/" + aid + "/tester-pool/accept", tester).status_code
                ),
                aids,
            )
        )
    assert sorted(statuses) == [200, 200, 409]
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count(TesterAssignment.id)).where(
                    TesterAssignment.tester_id == tester[0]
                )
            )
            == 2
        )


def test_concurrent_acceptance_cannot_overfill_app_or_circle(client):
    from concurrent.futures import ThreadPoolExecutor

    owner = actor()
    aid = campaign(owner)
    open_app(client, aid, owner)
    testers = [actor() for _ in range(16)]
    for tester in testers:
        post(client, "/tester-pool/me", tester, {"enabled": True})
    with ThreadPoolExecutor(max_workers=6) as workers:
        statuses = list(
            workers.map(
                lambda tester: (
                    post(client, "/apps/" + aid + "/tester-pool/accept", tester).status_code
                ),
                testers,
            )
        )
    assert statuses.count(200) == 14
    assert statuses.count(409) == 2


def test_inactive_accounts_cannot_participate(client):
    user = actor()
    with SessionLocal() as db:
        db.get(User, user[0]).is_active = False
        db.commit()
    assert client.get("/tester-pool/me", headers=user[1]).status_code == 403
    assert post(client, "/tester-pool/me", user, {"enabled": True}).status_code == 403
