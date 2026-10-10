from datetime import datetime, timezone

from fleet_monitor.domain import compute_status


def test_compute_status_with_missing_last_seen_is_offline() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert compute_status(None, now, 30) == "OFFLINE"


def test_compute_status_treats_zero_seconds_as_online() -> None:
    last_seen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    assert compute_status(last_seen, now, 30) == "ONLINE"


def test_compute_status_treats_just_under_timeout_as_online() -> None:
    last_seen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 1, 1, 12, 0, 29, 900000, tzinfo=timezone.utc)

    assert compute_status(last_seen, now, 30) == "ONLINE"


def test_compute_status_treats_exact_timeout_as_online() -> None:
    last_seen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 1, 1, 12, 0, 30, tzinfo=timezone.utc)

    assert compute_status(last_seen, now, 30) == "ONLINE"


def test_compute_status_treats_just_over_timeout_as_offline() -> None:
    last_seen = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 1, 1, 12, 0, 30, 1000, tzinfo=timezone.utc)

    assert compute_status(last_seen, now, 30) == "OFFLINE"
