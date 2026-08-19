from datetime import datetime, timezone


def get_now() -> datetime:
    """Production clock dependency. Tests override this dependency; release behavior stays real-time."""
    return datetime.now(timezone.utc)


def aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
