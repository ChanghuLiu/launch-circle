from datetime import datetime, timezone
import pytest
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.user import User
from app.models.launch import App, Circle, CircleMember, TesterAssignment as Assignment, TestMission as Mission

@pytest.fixture
def task(client):
    with SessionLocal() as db:
        owner=User(email='owner-group@example.invalid',login_email='owner-group@example.invalid')
        tester=User(email='tester-group@example.invalid',login_email='tester-group@example.invalid')
        db.add_all([owner,tester]);db.flush()
        circle=Circle(owner_id=owner.id,name='Group audit');db.add(circle);db.flush()
        db.add(CircleMember(circle_id=circle.id,user_id=tester.id,status='ACTIVE'))
        product=App(owner_id=owner.id,circle_id=circle.id,name='Test app',package_name='invalid.group.access',opt_in_url='https://play.google.com/apps/testing/invalid.group.access',google_group_configured=True)
        db.add(product);db.flush()
        row=Assignment(app_id=product.id,circle_id=circle.id,tester_id=tester.id,assignment_day=datetime.now(timezone.utc).date(),status='ASSIGNED')
        db.add(row);db.flush()
        mission=Mission(assignment_id=row.id,mission_type='INSTALL_FIRST_IMPRESSION',scheduled_day=1,status='AVAILABLE',due_at=datetime.now(timezone.utc))
        db.add(mission);db.commit();ids=(tester.id,row.id,mission.id)
    def actor(db: Session = Depends(get_db)):
        return db.get(User,ids[0])
    app.dependency_overrides[get_current_user]=actor
    yield ids
    app.dependency_overrides.pop(get_current_user,None)

def access(client,status='SELF_CONFIRMED',email='play-group@example.com'):
    return client.put('/tester-group-access',json={'play_email':email,'status':status})

@pytest.mark.parametrize('status',['NOT_JOINED','PENDING'])
def test_unjoined_and_pending_block_enrollment(client,task,status):
    assert access(client,status).status_code==200
    assert client.patch(f'/assignments/{task[1]}/opt-in').status_code==409
    assert client.patch(f'/assignments/{task[1]}/installed').status_code==409
    assert client.post(f'/missions/{task[2]}/start').status_code==409

def test_confirmation_persists_and_is_reported_honestly(client,task):
    assert client.get('/tester-group-access').json()['status']=='NOT_JOINED'
    response=access(client);assert response.status_code==200
    saved=client.get('/tester-group-access').json()
    assert saved['status']=='SELF_CONFIRMED' and saved['confirmed_at']
    assert saved['verification']=='USER_REPORTED'
    assert saved['group_email']=='launch-circle-12-testers@googlegroups.com'
    assert saved['play_email']=='play-group@example.com'

def test_confirmed_group_still_requires_optin_and_install(client,task):
    assert access(client).status_code==200
    assert client.patch(f'/assignments/{task[1]}/installed').status_code==409
    assert client.post(f'/missions/{task[2]}/start').status_code==409
    assert client.patch(f'/assignments/{task[1]}/opt-in').status_code==200
    assert client.post(f'/missions/{task[2]}/start').status_code==409
    assert client.patch(f'/assignments/{task[1]}/installed').status_code==200
    assert client.post(f'/missions/{task[2]}/start').status_code==200

def test_legacy_completion_cannot_manufacture_enrollment(client,task):
    assert access(client).status_code==200
    assert client.post(f'/test-assignments/{task[1]}/complete').status_code==409
    with SessionLocal() as db:
        row=db.get(Assignment,task[1])
        assert row.status=='ASSIGNED'
        assert row.opted_in_at is None and row.installed_at is None and row.completed_at is None

def test_account_change_requires_reenrollment(client,task):
    access(client)
    client.patch(f'/assignments/{task[1]}/opt-in')
    client.patch(f'/assignments/{task[1]}/installed')
    assert access(client,email='another-play@example.com').status_code==200
    assert client.post(f'/missions/{task[2]}/start').status_code==409
    assert client.patch(f'/assignments/{task[1]}/installed').status_code==409
    assert client.patch(f'/assignments/{task[1]}/opt-in').status_code==200
    with SessionLocal() as db:
        row=db.get(Assignment,task[1]);assert row.installed_at is None
        assert row.play_account_email=='another-play@example.com'
    assert client.patch(f'/assignments/{task[1]}/installed').status_code==200

def test_invalid_status_and_account_rejected(client,task):
    assert access(client,status='VERIFIED').status_code==422
    assert access(client,email='not-email').status_code==422

def test_reset_revokes_testing_without_deleting_history(client,task):
    access(client)
    client.patch(f'/assignments/{task[1]}/opt-in')
    client.patch(f'/assignments/{task[1]}/installed')
    access(client,status='NOT_JOINED')
    assert client.get('/tester-group-access').json()['confirmed_at'] is None
    assert client.post(f'/missions/{task[2]}/start').status_code==409
    with SessionLocal() as db: assert db.get(Assignment,task[1]).installed_at is not None
