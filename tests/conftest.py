"""Test fixtures for fleet monitor."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from fleet_monitor.api import create_app
from fleet_monitor.clock import FakeClock


@pytest.fixture
def fake_clock() -> FakeClock:
	return FakeClock(datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))


@pytest.fixture
def app(fake_clock: FakeClock):
	return create_app(clock=fake_clock, timeout=30)


@pytest.fixture
def client(app):
	with TestClient(app) as test_client:
		yield test_client


