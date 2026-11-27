from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.api.phase0 import mission_read
from app.api.phase0 import test_assignment_read as assignment_view
from app.core.database import SessionLocal
from app.models.launch import App, Feedback, TesterAssignment, TestMission
from app.models.pool import AppGroup, AppGroupTaskQueue
from tests.test_owner_app_group_selection import make_group
from tests.test_shared_pool import actor, campaign, open_app, post


def choose(client, app_id, group_id, owner):
    return post(client, f"/apps/{app_id}/app-groups/{group_id}/join", owner, {"consent": True})


def test_group_matching_capacity_and_join_consent(client):
    group_ids = [make_group("Daycare"), make_group("USB")]
    owners = [actor() for _ in range(16)]
    apps = []
    for index, owner in enumerate(owners):
        aid = campaign(owner)
        open_app(client, aid, owner)
        selected = group_ids[0] if index < 15 else group_ids[1]
        assert choose(client, aid, selected, owner).status_code == 200
        apps.append(aid)
    groups = client.get('/app-groups', headers=owners[0][1]).json()
    assert sorted(len(g['apps']) for g in groups) == [1, 15]
    own = next(g for g in groups if g['my_group'])
    assert own['joined'] and 'email' not in str(groups)
    with SessionLocal() as db:
        # Owner consent now occurs as part of explicitly selecting a group.
        assert db.scalar(select(TesterAssignment.id)) is not None
    for _ in range(2):
        assert post(client, '/app-groups/' + own['id'] + '/join', owners[0]).status_code == 200
    with SessionLocal() as db:
        assigned = db.scalars(select(TesterAssignment).where(TesterAssignment.tester_id == owners[0][0])).all()
        assert len(assigned) == 2
        assert all(a.app_id != apps[0] and a.opted_in_at is None and a.installed_at is None for a in assigned)
        assert db.scalar(select(func.count(AppGroupTaskQueue.id)).where(
            AppGroupTaskQueue.tester_id == owners[0][0],
            AppGroupTaskQueue.status == "PENDING",
        )) == 12
    assert post(client, '/app-groups/' + own['id'] + '/join', owners[-1]).status_code == 409


def test_later_group_app_creates_task_only_for_consented_member(client):
    first, second = actor(), actor()
    group_id = make_group("Daycare")
    a = campaign(first)
    open_app(client, a, first)
    assert choose(client, a, group_id, first).status_code == 200
    b = campaign(second)
    open_app(client, b, second)
    assert choose(client, b, group_id, second).status_code == 200
    with SessionLocal() as db:
        tasks = db.scalars(select(TesterAssignment)).all()
        assert len(tasks) == 2
        assert {(task.tester_id, task.app_id) for task in tasks} == {(first[0], b), (second[0], a)}


def test_group_queue_is_idempotent_and_dispatches_only_within_daily_limit(client):
    from app.main import app
    from app.services.clock import get_now

    group_id = make_group("Queue")
    owners = [actor() for _ in range(4)]
    apps = []
    for owner in owners:
        app_id = campaign(owner)
        open_app(client, app_id, owner)
        apps.append(app_id)
        assert choose(client, app_id, group_id, owner).status_code == 200

    with SessionLocal() as db:
        assigned = db.scalars(select(TesterAssignment).where(TesterAssignment.tester_id == owners[0][0])).all()
        pending = db.scalars(select(AppGroupTaskQueue).where(
            AppGroupTaskQueue.tester_id == owners[0][0], AppGroupTaskQueue.status == "PENDING",
        )).all()
        assert len(assigned) == 2
        assert len(pending) == 1 and pending[0].app_id == apps[3]

    from app.api.pool import sync_group
    with SessionLocal() as db:
        sync_group(db, group_id, datetime.now(UTC))
        db.commit()
    with SessionLocal() as db:
        assert db.scalar(select(func.count(AppGroupTaskQueue.id)).where(
            AppGroupTaskQueue.tester_id == owners[0][0],
        )) == 3

    # Completion frees the concurrent-work slots; the next UTC day can drain one queued item.
    with SessionLocal() as db:
        for row in db.scalars(select(TesterAssignment).where(TesterAssignment.tester_id == owners[0][0])):
            row.status = "COMPLETED"
        db.commit()
    previous = app.dependency_overrides.get(get_now)
    app.dependency_overrides[get_now] = lambda: datetime.now(UTC) + timedelta(days=1)
    try:
        assert client.get("/test-assignments/today", headers=owners[0][1]).status_code == 200
        assert client.get("/test-assignments/today", headers=owners[0][1]).status_code == 200
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_now, None)
        else:
            app.dependency_overrides[get_now] = previous
    with SessionLocal() as db:
        delivered = db.scalar(select(AppGroupTaskQueue).where(
            AppGroupTaskQueue.tester_id == owners[0][0], AppGroupTaskQueue.app_id == apps[3],
        ))
        assert delivered.status == "DISPATCHED"
        assert db.scalar(select(func.count(TesterAssignment.id)).where(
            TesterAssignment.tester_id == owners[0][0], TesterAssignment.app_id == apps[3],
        )) == 1


def test_closed_group_blocks_direct_and_admin_task_creation_and_keeps_existing_task(client):
    owner, tester = actor(), actor()
    group_id = make_group("Closed")
    app_id = campaign(owner)
    open_app(client, app_id, owner)
    assert choose(client, app_id, group_id, owner).status_code == 200
    peer_app = campaign(tester)
    open_app(client, peer_app, tester)
    assert choose(client, peer_app, group_id, tester).status_code == 200
    with SessionLocal() as db:
        existing = db.scalar(select(TesterAssignment).where(
            TesterAssignment.app_id == app_id, TesterAssignment.tester_id == tester[0],
        ))
        assert existing is not None
        existing_id = existing.id
        db.get(AppGroup, group_id).status = "CLOSED"
        db.commit()

    direct = post(client, f"/apps/{app_id}/tester-pool/accept", tester)
    manual = client.post(f"/apps/{app_id}/assign/{tester[0]}", headers=owner[1])
    assert direct.status_code == 409 and direct.json()["detail"] == "APP_GROUP_CLOSED"
    assert manual.status_code == 409 and manual.json()["detail"] == "APP_GROUP_CLOSED"
    with SessionLocal() as db:
        kept = db.get(TesterAssignment, existing_id)
        assert kept.status == "ASSIGNED"
        assert db.scalar(select(func.count(TesterAssignment.id)).where(
            TesterAssignment.app_id == app_id, TesterAssignment.tester_id == tester[0],
        )) == 1


def test_admin_assignment_observes_the_same_two_task_daily_limit(client):
    owner, tester, unrelated_owner = actor(), actor(), actor()
    group_id = make_group("Daily cap")
    target_app = campaign(owner)
    open_app(client, target_app, owner)
    assert choose(client, target_app, group_id, owner).status_code == 200
    tester_app = campaign(tester)
    open_app(client, tester_app, tester)
    assert choose(client, tester_app, group_id, tester).status_code == 200
    unrelated_app = campaign(unrelated_owner)
    with SessionLocal() as db:
        circle_id = db.get(App, unrelated_app).circle_id
        db.add(TesterAssignment(
            app_id=unrelated_app,
            circle_id=circle_id,
            tester_id=tester[0],
            assignment_day=datetime.now(UTC).date(),
            status="DROPPED",
        ))
        db.commit()
        before = db.scalar(select(func.count(TesterAssignment.id)).where(
            TesterAssignment.tester_id == tester[0],
            TesterAssignment.assignment_day == datetime.now(UTC).date(),
        ))
        assert before == 2

    response = client.post(f"/apps/{target_app}/assign/{tester[0]}", headers=owner[1])
    assert response.status_code == 409
    assert "daily assignment limit" in response.json()["detail"].lower()


def test_submitted_feedback_blocks_current_task_but_new_due_mission_reopens(client):
    owner, tester = actor(), actor()
    aid = campaign(owner)
    open_app(client, aid, owner)
    post(client, '/apps/' + aid + '/tester-pool/accept', tester)
    with SessionLocal() as db:
        task = db.scalar(select(TesterAssignment).where(TesterAssignment.tester_id == tester[0]))
        task.status = 'ACTIVE'
        mission = TestMission(assignment=task, mission_type='INSTALL_FIRST_IMPRESSION', scheduled_day=1, status='COMPLETED')
        db.add(mission);db.flush()
        assert not assignment_view(task).feedback_submitted
        db.add(Feedback(mission_id=mission.id, tester_id=tester[0], app_id=aid, created_at=datetime.now(UTC)))
        db.flush();db.expire(mission, ['feedback_entry'])
        assert assignment_view(task).feedback_submitted
        assert mission_read(mission).feedback_submitted
        new = TestMission(assignment=task, mission_type='INSTALL_FIRST_IMPRESSION', scheduled_day=3, status='AVAILABLE')
        db.add(new);db.flush()
        assert not assignment_view(task).feedback_submitted


def test_group_tasks_survive_next_day_without_implicit_copies(client):
    from datetime import timedelta

    from app.main import app
    from app.services.clock import get_now
    owner, other = actor(), actor()
    group_id = make_group("Daycare")
    for who in (owner, other):
        aid = campaign(who)
        open_app(client, aid, who)
        assert choose(client, aid, group_id, who).status_code == 200
    initial = client.get('/test-assignments/today', headers=owner[1]).json()
    assert len(initial) == 1
    previous = app.dependency_overrides.get(get_now)
    app.dependency_overrides[get_now] = lambda: datetime.now(UTC) + timedelta(days=1)
    try:
        later = client.get('/test-assignments/today', headers=owner[1]).json()
        assert [a['id'] for a in later] == [a['id'] for a in initial]
        with SessionLocal() as db:
            assert len(db.scalars(select(TesterAssignment)).all()) == 2
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_now, None)
        else:
            app.dependency_overrides[get_now] = previous


def test_leaving_full_group_reopens_slot_preserves_feedback_and_can_resume(client):
    from app.models.pool import AppGroupApp, AppGroupMember, PoolListing
    group_id = make_group("Daycare")
    owners = [actor() for _ in range(15)]
    app_ids = []
    for owner in owners:
        aid = campaign(owner);open_app(client, aid, owner);app_ids.append(aid)
        assert choose(client, aid, group_id, owner).status_code == 200
    group = next(g for g in client.get('/app-groups', headers=owners[0][1]).json() if g['id'] == group_id)
    assert group['status'] == 'FULL' and group['capacity'] == 15
    post(client, '/apps/' + app_ids[0] + '/pool-listing', owners[0], {'enabled': False})
    paused = client.get('/app-groups', headers=owners[0][1]).json()[0]
    # Recruitment approval belongs to the administrator and remains enabled
    # when an owner leaves the Group; the owner's App is removed from the Group.
    assert paused['status'] == 'FULL' and paused['occupied_slots'] == 15 and paused['my_group'] and paused['ready_to_join']
    open_app(client, app_ids[0], owners[0])
    for owner in owners:
        assert post(client, '/app-groups/' + group['id'] + '/join', owner).status_code == 200
    with SessionLocal() as db:
        task = db.scalar(select(TesterAssignment).where(TesterAssignment.app_id == app_ids[1], TesterAssignment.tester_id == owners[0][0]))
        mission = TestMission(assignment=task, mission_type='INSTALL_FIRST_IMPRESSION', scheduled_day=1, status='COMPLETED')
        db.add(mission);db.flush()
        db.add(Feedback(mission_id=mission.id, tester_id=owners[0][0], app_id=app_ids[1], created_at=datetime.now(UTC)));db.commit()
        mission_id = mission.id
    assert post(client, '/app-groups/' + group['id'] + '/leave', owners[0]).status_code == 200
    assert post(client, '/app-groups/' + group['id'] + '/leave', owners[0]).json()['already_left']
    visible = client.get('/app-groups', headers=owners[1][1]).json()[0]
    assert visible['status'] == 'FORMING' and len(visible['apps']) == 14
    with SessionLocal() as db:
        assert db.get(AppGroupMember, (group['id'], owners[0][0])) is None
        assert db.get(AppGroupApp, app_ids[0]) is None
        assert db.get(PoolListing, app_ids[0]).enabled
        assert db.scalar(select(Feedback).where(Feedback.mission_id == mission_id)) is not None
        assert all(t.status == 'DROPPED' for t in db.scalars(select(TesterAssignment).where(TesterAssignment.tester_id == owners[0][0])))
        assert db.scalar(select(func.count(AppGroupTaskQueue.id)).where(
            AppGroupTaskQueue.tester_id == owners[0][0],
            AppGroupTaskQueue.status == "CANCELLED",
        )) > 0
    # The freed slot can be filled by a new app; recruitment approval remains enabled.
    newcomer = actor();replacement = campaign(newcomer);open_app(client, replacement, newcomer)
    assert choose(client, replacement, group['id'], newcomer).status_code == 200
    with SessionLocal() as db:
        replacement_tasks = db.scalars(select(TesterAssignment).where(TesterAssignment.tester_id == newcomer[0])).all()
        assert len(replacement_tasks) == 2
    other_group = make_group("USB")
    assert choose(client, app_ids[0], other_group, owners[0]).status_code == 200
    own_group = next(g for g in client.get('/app-groups', headers=owners[0][1]).json() if g['my_group'])
    assert own_group['id'] == other_group


def test_resume_in_same_group_restores_tasks_without_duplicate_feedback(client):
    owners = [actor(), actor()]
    group_id = make_group("Daycare")
    ids=[]
    for who in owners:
        aid=campaign(who);open_app(client,aid,who);ids.append(aid)
        assert choose(client, aid, group_id, who).status_code == 200
    with SessionLocal() as db:
        original = db.scalar(select(TesterAssignment.id).where(TesterAssignment.tester_id==owners[0][0]))
    post(client,'/app-groups/'+group_id+'/leave',owners[0])
    open_app(client,ids[0],owners[0])
    assert choose(client, ids[0], group_id, owners[0]).status_code == 200
    with SessionLocal() as db:
        tasks=db.scalars(select(TesterAssignment).where(TesterAssignment.tester_id==owners[0][0])).all()
        assert len(tasks)==1 and tasks[0].id==original and tasks[0].status=='ASSIGNED'


def test_group_uses_first_app_name_and_keeps_it_for_later_members(client):
    from app.models.launch import App
    first, second = actor(), actor()
    group_id = make_group("Notes Escape Group")
    aid = campaign(first)
    with SessionLocal() as db:
        db.get(App, aid).name = 'Notes Escape'
        db.commit()
    open_app(client, aid, first)
    assert choose(client, aid, group_id, first).status_code == 200
    initial = next(g for g in client.get('/app-groups', headers=first[1]).json() if g['id'] == group_id)
    assert initial['name'] == 'Notes Escape Group'
    bid = campaign(second)
    open_app(client, bid, second)
    assert choose(client, bid, group_id, second).status_code == 200
    after = client.get('/app-groups', headers=first[1]).json()[0]
    assert after['id'] == initial['id'] and after['name'] == initial['name']
