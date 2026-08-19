import sqlite3

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, text

from app.core.config import DEVELOPMENT_JWT_SECRET, Settings, get_settings
from app.core.database import ensure_sqlite_parent, sqlite_database_path
from app.main import app
from app.services.sqlite_backup import create_backup, database_path


PILOT_SECRET = "pilot-test-secret-that-is-not-used-in-deployment"


def pilot_settings(tmp_path, **overrides):
    values = {
        "app_env": "pilot",
        "database_url": f"sqlite:///{tmp_path / "pilot.db"}",
        "jwt_secret": PILOT_SECRET,
        "public_base_url": "https://pilot.example.test",
        "cors_origins": "https://pilot.example.test",
        "development_auth_enabled": False,
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


def test_pilot_config_rejects_development_secret_and_unsafe_values(tmp_path):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        pilot_settings(tmp_path, jwt_secret=DEVELOPMENT_JWT_SECRET)
    with pytest.raises(ValidationError, match="absolute SQLite path"):
        pilot_settings(tmp_path, database_url="sqlite:///./relative.db")
    with pytest.raises(ValidationError, match="HTTPS"):
        pilot_settings(tmp_path, public_base_url="http://pilot.example.test")
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        pilot_settings(tmp_path, cors_origins="*")
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        pilot_settings(tmp_path, cors_origins="http://pilot.example.test")
    with pytest.raises(ValidationError, match="DEVELOPMENT_AUTH_ENABLED"):
        pilot_settings(tmp_path, development_auth_enabled=True)


def test_pilot_config_accepts_safe_environment_and_group_defaults(tmp_path):
    settings = pilot_settings(tmp_path)
    assert settings.is_deployment
    assert settings.launch_circle_invite_base_url == "https://launchcircle.app/join"
    assert settings.google_group_email == "launch-circle-12-testers@googlegroups.com"


def test_absolute_sqlite_parent_and_restart_persistence(tmp_path):
    db_path = tmp_path / "persistent" / "launch_circle.db"
    database_url = f"sqlite:///{db_path}"
    assert ensure_sqlite_parent(database_url) == db_path
    assert db_path.parent.is_dir()
    first = create_engine(database_url)
    with first.begin() as connection:
        connection.execute(text("CREATE TABLE rehearsal (value TEXT NOT NULL)"))
        connection.execute(text("INSERT INTO rehearsal VALUES (:value)"), {"value": "retained"})
    first.dispose()
    restarted = create_engine(database_url)
    with restarted.connect() as connection:
        assert connection.scalar(text("SELECT value FROM rehearsal")) == "retained"
    restarted.dispose()
    assert sqlite_database_path(database_url) == db_path


def test_sqlite_backup_is_consistent_and_retained(tmp_path):
    source = tmp_path / "live" / "launch_circle.db"
    source.parent.mkdir()
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        db.execute("INSERT INTO sample VALUES (?)", ("pilot-data",))
        db.commit()
    destination = tmp_path / "backups"
    first = create_backup(source, destination, keep=2)
    second = create_backup(source, destination, keep=2)
    third = create_backup(source, destination, keep=2)
    assert not first.exists()
    assert second.exists() and third.exists()
    with sqlite3.connect(third) as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("SELECT value FROM sample").fetchone() == ("pilot-data",)
    assert database_path(f"sqlite:///{source}") == source.resolve()


def test_health_checks_database_without_sensitive_details(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "database_url" not in response.text


def test_development_auth_disabled_in_pilot(client, tmp_path):
    settings = pilot_settings(tmp_path)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = client.post(
            "/auth/register",
            json={
                "email": "external@example.com",
                "password": "password123",
                "display_name": "External",
            },
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_no_acceptance_control_routes_are_exposed():
    paths = {route.path for route in app.routes}
    forbidden = {"/test-clock", "/acceptance/seed", "/acceptance/reset", "/reset", "/seed"}
    assert paths.isdisjoint(forbidden)
