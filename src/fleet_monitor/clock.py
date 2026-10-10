"""Clock abstractions for the fleet monitor."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Protocol


class Clock(Protocol):
	"""Protocol for objects that can provide the current UTC time."""

	def now(self) -> datetime:
		"""Return the current time as an aware UTC datetime."""


@dataclass(slots=True)
class SystemClock:
	"""Clock implementation backed by the system clock."""

	def now(self) -> datetime:
		return datetime.now(timezone.utc)


@dataclass(slots=True)
class FakeClock:
	"""Test clock whose time can be controlled explicitly."""

	current: datetime
	_lock: Lock = field(default_factory=Lock, init=False, repr=False)

	def now(self) -> datetime:
		with self._lock:
			return self.current

	def advance(self, seconds: float) -> None:
		with self._lock:
			self.current = self.current + timedelta(seconds=seconds)

	def set(self, moment: datetime) -> None:
		with self._lock:
			self.current = moment


