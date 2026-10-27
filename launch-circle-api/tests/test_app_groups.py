from datetime import UTC, datetime
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.launch import TesterAssignment, TestMission, Feedback
from app.api.phase0 import test_assignment_read as assignment_view, mission_read
from tests.test_shared_pool import actor, campaign, open_app, post


def test_group_matching_capacity_and_join_consent(client):
    owners = [actor() for _ in range(14)]
    apps = []
    for owner in owners:
        aid = campaign(owner)
        open_app(client, aid, owner)
        apps.append(aid)
    groups = client.get('/app-groups', headers=owners[0][1]).json()
    assert sorted(len(g['apps']) for g in groups) == [1, 13]
    own = next(g for g in groups if g['my_group'])
    assert not own['joined'] and 'email' not in str(groups)
    with SessionLocal() as db:
        assert db.scalar(select(TesterAssignment.id)) is None
    for _ in range(2):
        assert post(client, '/app-groups/' + own['id'] + '/join', owners[0]).status_code == 200
    with SessionLocal() as db:
        assigned = db.scalars(select(TesterAssignment).where(TesterAssignment.tester_id == owners[0][0])).all()
        assert len(assigned) == 12
        assert all(a.app_id != apps[0] and a.opted_in_at is None and a.installed_at is None for a in assigned)
    assert post(client, '/app-groups/' + own['id'] + '/join', owners[-1]).status_code == 409


def test_later_group_app_creates_task_only_for_consented_member(client):
    first, second = actor(), actor()
    a = campaign(first)
    open_app(client, a, first)
    group = client.get('/app-groups', headers=first[1]).json()[0]
    assert post(client, '/app-groups/' + group['id'] + '/join', first).status_code == 200
    b = campaign(second)
    open_app(client, b, second)
    with SessionLocal() as db:
        tasks = db.scalars(select(TesterAssignment)).all()
        assert len(tasks) == 1 and tasks[0].tester_id == first[0] and tasks[0].app_id == b


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
    for who in (owner, other):
        aid = campaign(who)
        open_app(client, aid, who)
    group = client.get('/app-groups', headers=owner[1]).json()[0]
    post(client, '/app-groups/' + group['id'] + '/join', owner)
    initial = client.get('/test-assignments/today', headers=owner[1]).json()
    assert len(initial) == 1
    previous = app.dependency_overrides.get(get_now)
    app.dependency_overrides[get_now] = lambda: datetime.now(UTC) + timedelta(days=1)
    try:
        later = client.get('/test-assignments/today', headers=owner[1]).json()
        assert [a['id'] for a in later] == [a['id'] for a in initial]
        with SessionLocal() as db:
            assert len(db.scalars(select(TesterAssignment)).all()) == 1
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_now, None)
        else:
            app.dependency_overrides[get_now] = previous
