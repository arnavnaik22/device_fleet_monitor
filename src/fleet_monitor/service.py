"""Application services for device operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .clock import Clock
from .domain import Device, compute_status
from .errors import DeviceNotFound
from .store import DeviceStore


@dataclass(slots=True)
class DeviceService:
	"""Use-case layer for device operations."""

	store: DeviceStore
	clock: Clock
	timeout_seconds: int

	def register_device(self, device_id: str, name: str) -> Device:
		now = self.clock.now()
		device = Device(id=device_id, name=name, registered_at=now)
		return self.store.add(device)

	def get_device(self, device_id: str) -> Device:
		return self.store.get(device_id)

	def record_heartbeat(
		self,
		device_id: str,
		*,
		timestamp: datetime | None,
		status: str,
		cpu_usage: float | None,
		signal_strength: int | None,
	) -> Device:
		device = self.store.get(device_id)
		seen_at = self.clock.now()
		heartbeat_timestamp = timestamp or seen_at
		overwrite_latest = (
			device.last_heartbeat is None or heartbeat_timestamp >= device.last_heartbeat
		)
		latest_timestamp = heartbeat_timestamp if overwrite_latest else device.last_heartbeat
		heartbeat_status = status if overwrite_latest else device.reported_status or status
		heartbeat_cpu = cpu_usage if overwrite_latest else device.cpu_usage
		heartbeat_signal = signal_strength if overwrite_latest else device.signal_strength
		return self.store.update_heartbeat(
			device_id,
			last_seen_at=seen_at,
			last_heartbeat=latest_timestamp,
			reported_status=heartbeat_status,
			cpu_usage=heartbeat_cpu,
			signal_strength=heartbeat_signal,
			overwrite_latest=overwrite_latest,
		)

	def list_devices(self, status: str | None = None) -> tuple[list[Device], datetime]:
		now = self.clock.now()
		devices = sorted(self.store.snapshot(), key=lambda device: device.id)
		if status is None:
			return devices, now

		filtered = [
			device
			for device in devices
			if compute_status(device.last_seen_at, now, self.timeout_seconds) == status
		]
		return filtered, now

	def summary(self) -> tuple[dict[str, int], datetime]:
		now = self.clock.now()
		devices = self.store.snapshot()
		online = sum(
			1
			for device in devices
			if compute_status(device.last_seen_at, now, self.timeout_seconds)
			== "ONLINE"
		)
		offline = len(devices) - online
		return {"total": len(devices), "online": online, "offline": offline}, now

