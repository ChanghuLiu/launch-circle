from sqlalchemy import text

from app.core.database import engine


def _set_revision(revision: str) -> None:
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS alembic_version "
            "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
        )
        connection.exec_driver_sql("DELETE FROM alembic_version")
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": revision},
        )


def test_0019_capabilities_are_disabled_and_read_only(client):
    _set_revision("0019_user_activity_events")

    with engine.connect() as connection:
        before = connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
    response = client.get("/capabilities")
    with engine.connect() as connection:
        after = connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one()

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": 1,
        "migration_revision": "0019_user_activity_events",
        "capabilities": {"owner_attestation": False, "app_group_selection": False},
    }
    assert after == before
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM user_activity_events")).scalar_one() == 0


def test_0021_capabilities_are_enabled_when_schema_matches(client):
    _set_revision("0021_group_task_queue")

    response = client.get("/capabilities")

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": 1,
        "migration_revision": "0021_group_task_queue",
        "capabilities": {"owner_attestation": True, "app_group_selection": True},
    }


def test_unknown_revision_fails_closed(client):
    _set_revision("0022_unknown")
    response = client.get("/capabilities")
    assert response.json()["capabilities"] == {
        "owner_attestation": False,
        "app_group_selection": False,
    }
