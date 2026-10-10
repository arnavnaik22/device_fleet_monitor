"""Domain exceptions for fleet monitor operations."""


class DeviceAlreadyExists(Exception):
	"""Raised when a device id is already registered."""


class DeviceNotFound(Exception):
	"""Raised when a requested device cannot be found."""

