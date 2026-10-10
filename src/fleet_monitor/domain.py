"""Domain logic for devices and status computation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal


DeviceStatus = Literal["ONLINE", "OFFLINE"]


@dataclass(slots=True)
class Device:
	"""Stored device state."""

	id: str
	name: str
	registered_at: datetime
	last_seen_at: datetime | None = None
	last_heartbeat: datetime | None = None
	reported_status: str | None = None
	cpu_usage: float | None = None
	signal_strength: int | None = None


def compute_status(
	last_seen_at: datetime | None,
	now: datetime,
	timeout_seconds: int,
) -> DeviceStatus:
	"""Compute the current status from the last receipt time and now."""

	if last_seen_at is None:
		return "OFFLINE"
	if now - last_seen_at <= timedelta(seconds=timeout_seconds):
		return "ONLINE"
	return "OFFLINE"

