"""Pydantic schemas for the fleet monitor API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictInt, field_validator

from .domain import Device, compute_status

ID_PATTERN = r"^[A-Za-z0-9._-]{1,64}$"
HEARTBEAT_STATUSES = {"OK", "DEGRADED", "ERROR"}


def format_timestamp(value: datetime | None) -> str | None:
	"""Format datetimes as UTC ISO-8601 strings with a trailing Z."""

	if value is None:
		return None
	if value.tzinfo is None or value.utcoffset() is None:
		value = value.replace(tzinfo=timezone.utc)
	value = value.astimezone(timezone.utc)
	return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


class DeviceRegistrationRequest(BaseModel):
	"""Request body for device registration."""

	id: str = Field(pattern=ID_PATTERN)
	name: str

	@field_validator("name")
	@classmethod
	def validate_name(cls, value: str) -> str:
		cleaned = value.strip()
		if not cleaned:
			raise ValueError("name must not be empty")
		if len(cleaned) > 128:
			raise ValueError("name must be at most 128 characters")
		return cleaned


class HeartbeatRequest(BaseModel):
	"""Request body for device heartbeat ingestion."""

	timestamp: datetime | None = None
	status: str
	cpu_usage: float | None = None
	signal_strength: Annotated[StrictInt | None, Field(default=None)] = None

	@field_validator("timestamp")
	@classmethod
	def normalize_timestamp(cls, value: datetime | None) -> datetime | None:
		if value is None:
			return None
		if value.tzinfo is None or value.utcoffset() is None:
			return value.replace(tzinfo=timezone.utc)
		return value.astimezone(timezone.utc)

	@field_validator("status")
	@classmethod
	def normalize_status(cls, value: str) -> str:
		cleaned = value.strip().upper()
		if cleaned not in HEARTBEAT_STATUSES:
			raise ValueError("status must be one of OK, DEGRADED, ERROR")
		return cleaned

	@field_validator("cpu_usage")
	@classmethod
	def validate_cpu_usage(cls, value: float | None) -> float | None:
		if value is None:
			return None
		if not 0 <= value <= 100:
			raise ValueError("cpu_usage must be between 0 and 100")
		return value


class RegistrationResponse(BaseModel):
	"""Response body for registration."""

	id: str
	name: str
	status: Literal["ONLINE", "OFFLINE"]
	last_heartbeat: str | None


class DeviceResponse(BaseModel):
	"""Full device representation returned by the API."""

	id: str
	name: str
	status: Literal["ONLINE", "OFFLINE"]
	registered_at: str
	last_seen_at: str | None
	last_heartbeat: str | None
	reported_status: str | None
	cpu_usage: float | None
	signal_strength: int | None


class HeartbeatResponse(BaseModel):
	"""Response body for heartbeat ingestion."""

	id: str
	status: Literal["ONLINE", "OFFLINE"]
	last_heartbeat: str | None


class SummaryResponse(BaseModel):
	"""Fleet summary counts."""

	total: int
	online: int
	offline: int


def device_to_registration_response(
	device: Device,
	*,
	now: datetime,
	timeout_seconds: int,
) -> dict[str, object]:
	"""Serialize a device as the registration response shape."""

	return {
		"id": device.id,
		"name": device.name,
		"status": compute_status(device.last_seen_at, now, timeout_seconds),
		"last_heartbeat": format_timestamp(device.last_heartbeat),
	}


def device_to_full_response(
	device: Device,
	*,
	now: datetime,
	timeout_seconds: int,
) -> dict[str, object]:
	"""Serialize a device with all API-visible fields."""

	return {
		"id": device.id,
		"name": device.name,
		"status": compute_status(device.last_seen_at, now, timeout_seconds),
		"registered_at": format_timestamp(device.registered_at),
		"last_seen_at": format_timestamp(device.last_seen_at),
		"last_heartbeat": format_timestamp(device.last_heartbeat),
		"reported_status": device.reported_status,
		"cpu_usage": device.cpu_usage,
		"signal_strength": device.signal_strength,
	}


def device_to_heartbeat_response(
	device: Device,
	*,
	now: datetime,
	timeout_seconds: int,
) -> dict[str, object]:
	"""Serialize a device as the heartbeat response shape."""

	return {
		"id": device.id,
		"status": compute_status(device.last_seen_at, now, timeout_seconds),
		"last_heartbeat": format_timestamp(device.last_heartbeat),
	}

