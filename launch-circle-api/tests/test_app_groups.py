from datetime import UTC, datetime
from sqlalchemy import select
from app.core.database import SessionLocal
from app.models.launch import TesterAssignment, TestMission, Feedback
from app.api.phase0 import test_assignment_read as assignment_view, mission_read
from tests.test_shared_pool import actor, campaign, open_app, post


def test_group_matching_capacity_and_join_consent(client):
    owners = [actor() for _ in range(16)]
    apps = []
    for owner in owners:
        aid = campaign(owner)
        open_app(client, aid, owner)
        apps.append(aid)
    groups = client.get('/app-groups', headers=owners[0][1]).json()
    assert sorted(len(g['apps']) for g in groups) == [1, 15]
    own = next(g for g in groups if g['my_group'])
    assert not own['joined'] and 'email' not in str(groups)
    with SessionLocal() as db:
        assert db.scalar(select(TesterAssignment.id)) is None
    for _ in range(2):
        assert post(client, '/app-groups/' + own['id'] + '/join', owners[0]).status_code == 200
    with SessionLocal() as db:
        assigned = db.scalars(select(TesterAssignment).where(TesterAssignment.tester_id == owners[0][0])).all()
        assert len(assigned) == 14
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


def test_leaving_full_group_reopens_slot_preserves_feedback_and_can_resume(client):
    from app.models.pool import AppGroupApp, AppGroupMember, PoolListing
    owners = [actor() for _ in range(15)]
    app_ids = []
    for owner in owners:
        aid = campaign(owner);open_app(client, aid, owner);app_ids.append(aid)
    group = client.get('/app-groups', headers=owners[0][1]).json()[0]
    assert group['status'] == 'FULL' and group['capacity'] == 15
    post(client, '/apps/' + app_ids[0] + '/pool-listing', owners[0], {'enabled': False})
    paused = client.get('/app-groups', headers=owners[0][1]).json()[0]
    assert paused['status'] == 'FULL' and paused['occupied_slots'] == 15 and paused['my_group'] and not paused['ready_to_join']
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
        assert not db.get(PoolListing, app_ids[0]).enabled
        assert db.scalar(select(Feedback).where(Feedback.mission_id == mission_id)) is not None
        assert all(t.status == 'DROPPED' for t in db.scalars(select(TesterAssignment).where(TesterAssignment.tester_id == owners[0][0])))
    # The freed slot can be filled by a new app; the departing owner stays paused.
    newcomer = actor();replacement = campaign(newcomer);open_app(client, replacement, newcomer)
    assert client.get('/app-groups', headers=newcomer[1]).json()[0]['status'] == 'FULL'
    assert post(client, '/app-groups/' + group['id'] + '/join', newcomer).status_code == 200
    with SessionLocal() as db:
        replacement_tasks = db.scalars(select(TesterAssignment).where(TesterAssignment.tester_id == newcomer[0])).all()
        assert len(replacement_tasks) == 14
    open_app(client, app_ids[0], owners[0])
    own_group = next(g for g in client.get('/app-groups', headers=owners[0][1]).json() if g['my_group'])
    assert own_group['id'] != group['id']


def test_resume_in_same_group_restores_tasks_without_duplicate_feedback(client):
    owners = [actor(), actor()]
    ids=[]
    for who in owners:
        aid=campaign(who);open_app(client,aid,who);ids.append(aid)
    group=client.get('/app-groups',headers=owners[0][1]).json()[0]
    post(client,'/app-groups/'+group['id']+'/join',owners[0])
    with SessionLocal() as db:
        original = db.scalar(select(TesterAssignment.id).where(TesterAssignment.tester_id==owners[0][0]))
    post(client,'/app-groups/'+group['id']+'/leave',owners[0])
    open_app(client,ids[0],owners[0])
    post(client,'/app-groups/'+group['id']+'/join',owners[0])
    with SessionLocal() as db:
        tasks=db.scalars(select(TesterAssignment).where(TesterAssignment.tester_id==owners[0][0])).all()
        assert len(tasks)==1 and tasks[0].id==original and tasks[0].status=='ASSIGNED'


def test_group_uses_first_app_name_and_keeps_it_for_later_members(client):
    from app.models.launch import App
    first, second = actor(), actor()
    aid = campaign(first)
    with SessionLocal() as db:
        db.get(App, aid).name = 'Notes Escape'
        db.commit()
    open_app(client, aid, first)
    initial = client.get('/app-groups', headers=first[1]).json()[0]
    assert initial['name'] == 'Notes Escape Group'
    bid = campaign(second)
    open_app(client, bid, second)
    after = client.get('/app-groups', headers=first[1]).json()[0]
    assert after['id'] == initial['id'] and after['name'] == initial['name']
