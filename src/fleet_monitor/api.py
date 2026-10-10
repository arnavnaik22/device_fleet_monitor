"""FastAPI application module."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Path, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .clock import Clock, SystemClock
from .config import HEARTBEAT_TIMEOUT_SECONDS
from .errors import DeviceAlreadyExists, DeviceNotFound
from .models import (
	DeviceRegistrationRequest,
	HeartbeatRequest,
	device_to_full_response,
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

	@app.exception_handler(RequestValidationError)
	async def request_validation_handler(_, exc: RequestValidationError):
		return JSONResponse(
			status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
			content={"detail": exc.errors()},
		)

	@app.get("/health")
	def health() -> dict[str, str]:
		return {"status": "ok"}

	@app.post("/devices", status_code=status.HTTP_201_CREATED)
	def register_device(payload: DeviceRegistrationRequest):
		device = service.register_device(payload.id, payload.name)
		return device_to_registration_response(
			device,
			now=service.clock.now(),
			timeout_seconds=service.timeout_seconds,
		)

	@app.get("/devices/{device_id}")
	def get_device(
		device_id: str = Path(..., pattern=r"^[A-Za-z0-9._-]{1,64}$"),
	):
		device = service.get_device(device_id)
		return device_to_full_response(
			device,
			now=service.clock.now(),
			timeout_seconds=service.timeout_seconds,
		)

	return app


app = create_app()

