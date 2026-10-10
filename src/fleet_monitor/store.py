"""In-memory device store."""

from __future__ import annotations

from dataclasses import replace
from threading import Lock
from datetime import datetime

from .domain import Device
from .errors import DeviceAlreadyExists, DeviceNotFound


class DeviceStore:
	"""Thread-safe in-memory device storage."""

	def __init__(self) -> None:
		self._devices: dict[str, Device] = {}
		self._lock = Lock()

	def add(self, device: Device) -> Device:
		with self._lock:
			if device.id in self._devices:
				raise DeviceAlreadyExists(device.id)
			self._devices[device.id] = replace(device)
			return replace(self._devices[device.id])

	def get(self, device_id: str) -> Device:
		with self._lock:
			device = self._devices.get(device_id)
			if device is None:
				raise DeviceNotFound(device_id)
			return replace(device)

	def update_heartbeat(
		self,
		device_id: str,
		*,
		last_seen_at: datetime,
		last_heartbeat: datetime,
		reported_status: str,
		cpu_usage: float | None,
		signal_strength: int | None,
		overwrite_latest: bool,
	) -> Device:
		with self._lock:
			device = self._devices.get(device_id)
			if device is None:
				raise DeviceNotFound(device_id)

			device.last_seen_at = last_seen_at
			if overwrite_latest:
				device.last_heartbeat = last_heartbeat
				device.reported_status = reported_status
				device.cpu_usage = cpu_usage
				device.signal_strength = signal_strength
			return replace(device)

	def snapshot(self) -> list[Device]:
		with self._lock:
			return [replace(device) for device in self._devices.values()]

