"""CLI simulator for fleet devices."""

from __future__ import annotations

import argparse
import random
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx


def utc_now() -> datetime:
	"""Return the current UTC time without microseconds."""

	return datetime.now(timezone.utc).replace(microsecond=0)


def format_utc(moment: datetime) -> str:
	"""Format a datetime as an ISO-8601 UTC string with Z suffix."""

	return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
		"+00:00", "Z"
	)


def parse_stop_after(value: str) -> tuple[str, float]:
	"""Parse a stop-after value of the form device-03:20."""

	device_id, seconds_text = value.split(":", 1)
	return device_id, float(seconds_text)


@dataclass(slots=True)
class DeviceControl:
	"""Per-device control state shared across threads."""

	enabled: threading.Event = field(default_factory=threading.Event)


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Mini Device Fleet Monitor simulator")
	parser.add_argument("--base-url", default="http://localhost:8000")
	parser.add_argument("--devices", type=int, default=5)
	parser.add_argument("--interval", type=float, default=5.0)
	parser.add_argument("--stop-after", type=parse_stop_after)
	parser.add_argument("--cpu", action=argparse.BooleanOptionalAction, default=True)
	parser.add_argument("--signal", action=argparse.BooleanOptionalAction, default=True)
	return parser


def register_device(client: httpx.Client, device_id: str) -> bool:
	"""Register a device, tolerating already-registered responses."""

	try:
		response = client.post(
			"/devices",
			json={"id": device_id, "name": f"Simulated {device_id}"},
		)
	except httpx.RequestError as exc:
		raise RuntimeError(f"unable to reach server: {exc}") from exc

	if response.status_code == 201:
		return True
	if response.status_code == 409:
		return True
	raise RuntimeError(f"unexpected registration response for {device_id}: {response.status_code}")


def heartbeat_payload(cpu_jitter: bool, signal_jitter: bool) -> dict[str, object]:
	moment = utc_now()
	cpu_usage = random.uniform(20, 80) if cpu_jitter else 50.0
	signal_strength = random.randint(-90, -50) if signal_jitter else -70
	return {
		"timestamp": format_utc(moment),
		"status": "OK",
		"cpu_usage": round(cpu_usage, 1),
		"signal_strength": signal_strength,
	}


def run_device_worker(
	base_url: str,
	device_id: str,
	control: DeviceControl,
	stop_all: threading.Event,
	interval: float,
	cpu_jitter: bool,
	signal_jitter: bool,
) -> None:
	with httpx.Client(base_url=base_url, timeout=5.0) as client:
		while not stop_all.is_set():
			if not control.enabled.is_set():
				if stop_all.wait(0.2):
					break
				continue

			try:
				response = client.post(f"/devices/{device_id}/heartbeat", json=heartbeat_payload(cpu_jitter, signal_jitter))
			except httpx.RequestError as exc:
				print(f"[{format_utc(utc_now())}] {device_id} heartbeat failed: unable to reach server ({exc})", flush=True)
				stop_all.set()
				break

			print(f"[{format_utc(utc_now())}] {device_id} heartbeat sent ({response.status_code})", flush=True)

			if response.status_code != 202:
				print(f"[{format_utc(utc_now())}] {device_id} unexpected response, stopping simulator", flush=True)
				stop_all.set()
				break

			if stop_all.wait(interval):
				break


def command_loop(
	controls: dict[str, DeviceControl],
	stop_all: threading.Event,
) -> None:
	try:
		while not stop_all.is_set():
			command = input().strip()
			if not command:
				continue
			if command == "quit":
				stop_all.set()
				return
			action, _, device_id = command.partition(" ")
			if action not in {"stop", "start"} or not device_id:
				print("Commands: stop device-03, start device-03, quit", flush=True)
				continue
			control = controls.get(device_id)
			if control is None:
				print(f"Unknown device: {device_id}", flush=True)
				continue
			if action == "stop":
				control.enabled.clear()
				print(f"[{format_utc(utc_now())}] {device_id} stopped", flush=True)
			else:
				control.enabled.set()
				print(f"[{format_utc(utc_now())}] {device_id} started", flush=True)
	except EOFError:
		return


def stop_after_timer(controls: dict[str, DeviceControl], stop_spec: tuple[str, float], stop_all: threading.Event) -> None:
	device_id, seconds = stop_spec
	if seconds <= 0:
		return
	if stop_all.wait(seconds):
		return
	control = controls.get(device_id)
	if control is not None:
		control.enabled.clear()
		print(f"[{format_utc(utc_now())}] {device_id} stopped by timer", flush=True)


def main(argv: list[str] | None = None) -> int:
	parser = build_parser()
	args = parser.parse_args(argv)

	stop_all = threading.Event()
	controls: dict[str, DeviceControl] = {}
	worker_threads: list[threading.Thread] = []

	with httpx.Client(base_url=args.base_url, timeout=5.0) as client:
		try:
			health = client.get("/health")
			health.raise_for_status()
		except httpx.RequestError as exc:
			print(f"Unable to reach server at {args.base_url}: {exc}", file=sys.stderr)
			return 1
		except httpx.HTTPStatusError as exc:
			print(f"Server at {args.base_url} did not return a healthy response: {exc.response.status_code}", file=sys.stderr)
			return 1

		try:
			for index in range(1, args.devices + 1):
				device_id = f"device-{index:02d}"
				register_device(client, device_id)
				control = DeviceControl()
				control.enabled.set()
				controls[device_id] = control
		except RuntimeError as exc:
			print(str(exc), file=sys.stderr)
			return 1

	for device_id, control in controls.items():
		thread = threading.Thread(
			target=run_device_worker,
			args=(args.base_url, device_id, control, stop_all, args.interval, args.cpu, args.signal),
			daemon=True,
		)
		thread.start()
		worker_threads.append(thread)

	input_thread = None
	if sys.stdin.isatty():
		input_thread = threading.Thread(target=command_loop, args=(controls, stop_all), daemon=True)
		input_thread.start()

	timer_thread = None
	if args.stop_after is not None:
		timer_thread = threading.Thread(
			target=stop_after_timer,
			args=(controls, args.stop_after, stop_all),
			daemon=True,
		)
		timer_thread.start()

	try:
		while not stop_all.wait(0.2):
			if not any(thread.is_alive() for thread in worker_threads):
				break
	except KeyboardInterrupt:
		stop_all.set()
	finally:
		stop_all.set()
		for thread in worker_threads:
			thread.join(timeout=2)
		if timer_thread is not None:
			timer_thread.join(timeout=1)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())

