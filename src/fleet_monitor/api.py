"""FastAPI application module."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, Path, Query, status
from fastapi.responses import JSONResponse

from .clock import Clock, SystemClock
from .config import HEARTBEAT_TIMEOUT_SECONDS
from .errors import DeviceAlreadyExists, DeviceNotFound
from .models import (
	DeviceRegistrationRequest,
	HeartbeatRequest,
	HeartbeatResponse,
	RegistrationResponse,
	SummaryResponse,
	DeviceResponse,
	device_to_full_response,
	device_to_heartbeat_response,
	device_to_registration_response,
)
from .service import DeviceService
from .store import DeviceStore


def create_app(clock: Clock | None = None, timeout: int | None = None) -> FastAPI:
	"""Create and configure the FastAPI application."""

	app = FastAPI(title="Mini Device Fleet Monitor")
	service = DeviceService(
		store=DeviceStore(),
		clock=clock or SystemClock(),
		timeout_seconds=timeout if timeout is not None else HEARTBEAT_TIMEOUT_SECONDS,
	)
	app.state.service = service

	@app.exception_handler(DeviceAlreadyExists)
	async def device_already_exists_handler(_, exc: DeviceAlreadyExists):
		return JSONResponse(
			status_code=status.HTTP_409_CONFLICT,
			content={"detail": f"Device '{exc.args[0]}' already exists"},
		)

	@app.exception_handler(DeviceNotFound)
	async def device_not_found_handler(_, exc: DeviceNotFound):
		return JSONResponse(
			status_code=status.HTTP_404_NOT_FOUND,
			content={"detail": f"Device '{exc.args[0]}' not found"},
		)

	@app.get("/health")
	def health() -> dict[str, str]:
		return {"status": "ok"}

	@app.post("/devices", status_code=status.HTTP_201_CREATED)
	def register_device(payload: DeviceRegistrationRequest) -> RegistrationResponse:
		device = service.register_device(payload.id, payload.name)
		return device_to_registration_response(
			device,
			now=service.clock.now(),
			timeout_seconds=service.timeout_seconds,
		)

	@app.get("/devices/{device_id}")
	def get_device(
		device_id: str = Path(..., pattern=r"^[A-Za-z0-9._-]{1,64}$"),
	) -> DeviceResponse:
		device = service.get_device(device_id)
		return device_to_full_response(
			device,
			now=service.clock.now(),
			timeout_seconds=service.timeout_seconds,
		)

	@app.post("/devices/{device_id}/heartbeat", status_code=status.HTTP_202_ACCEPTED)
	def record_heartbeat(
		payload: HeartbeatRequest,
		device_id: str = Path(..., pattern=r"^[A-Za-z0-9._-]{1,64}$"),
	) -> HeartbeatResponse:
		device = service.record_heartbeat(
			device_id,
			timestamp=payload.timestamp,
			status=payload.status,
			cpu_usage=payload.cpu_usage,
			signal_strength=payload.signal_strength,
		)
		return device_to_heartbeat_response(
			device,
			now=service.clock.now(),
			timeout_seconds=service.timeout_seconds,
		)

	@app.get("/devices")
	def list_devices(
		device_status: Literal["ONLINE", "OFFLINE"] | None = Query(
			default=None, alias="status"
		),
	) -> list[DeviceResponse]:
		devices, now = service.list_devices(device_status)
		return [
			device_to_full_response(
				device,
				now=now,
				timeout_seconds=service.timeout_seconds,
			)
			for device in devices
		]

	@app.get("/summary")
	def get_summary() -> SummaryResponse:
		summary, _ = service.summary()
		return summary

	return app


app = create_app()

