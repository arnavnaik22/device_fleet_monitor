"""Configuration helpers for the fleet monitor."""

from __future__ import annotations

import os


def _get_int(name: str, default: int) -> int:
	raw_value = os.getenv(name)
	if raw_value is None or raw_value.strip() == "":
		return default
	return int(raw_value)


HEARTBEAT_TIMEOUT_SECONDS = _get_int("HEARTBEAT_TIMEOUT_SECONDS", 30)
HOST = os.getenv("HOST", "127.0.0.1")
PORT = _get_int("PORT", 8000)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

