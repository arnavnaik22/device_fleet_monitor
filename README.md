# Mini Device Fleet Monitor

Fleet Monitor is a small FastAPI service for tracking a set of registered devices, their latest heartbeat, and a derived online/offline status based on a 30 second heartbeat timeout.

## What The Project Does

The service lets you register devices, ingest heartbeats, inspect device details, list the fleet, and fetch a live summary. A companion simulator can register five sample devices and keep them heartbeating so you can see one device move offline after you stop it.

## Design / Architecture

The application is intentionally simple and split into a few small layers:

- `src/fleet_monitor/domain.py` holds the device model and the status calculation.
- `src/fleet_monitor/store.py` is a thread-safe in-memory device store.
- `src/fleet_monitor/service.py` contains the use-case layer for registration, heartbeat updates, listing, and summary generation.
- `src/fleet_monitor/models.py` defines request and response schemas plus serialization helpers.
- `src/fleet_monitor/api.py` exposes the FastAPI routes.
- `simulator/simulate.py` drives a live heartbeat simulation from the terminal.

The status rule is straightforward: a device is `ONLINE` when its last seen time is within the configured timeout window, otherwise it is `OFFLINE`.

## Prerequisites

- Python 3.11+.
- `pip` for dependency installation.

## Build / Install

```bash
pip install -r requirements.txt
```

## Run The Application

```bash
uvicorn --app-dir src fleet_monitor.api:app --host 127.0.0.1 --port 8000
```

Environment variables:

- `HEARTBEAT_TIMEOUT_SECONDS` controls the online/offline threshold.
- `HOST`, `PORT`, and `LOG_LEVEL` are available for process configuration.

## Run The Simulator

```bash
python simulator/simulate.py --devices 5 --interval 5
```

Interactive controls while the simulator is running:

- `stop device-03` stops that device's heartbeat loop.
- `start device-03` resumes that device.
- `quit` stops the simulator.

If stdin is not interactive, you can still use `--stop-after device-03:20` to stop a device after a delay.

## Run The Tests

```bash
pytest -q
```

## Example API Requests

Register a device:

```bash
curl -X POST http://127.0.0.1:8000/devices \
	-H 'Content-Type: application/json' \
	-d '{"id":"device-01","name":"Lab Device 01"}'
```

Send a heartbeat:

```bash
curl -X POST http://127.0.0.1:8000/devices/device-01/heartbeat \
	-H 'Content-Type: application/json' \
	-d '{"timestamp":"2026-09-21T10:30:00Z","status":"OK","cpu_usage":42,"signal_strength":-71}'
```

Inspect a device:

```bash
curl http://127.0.0.1:8000/devices/device-01
```

List online devices only:

```bash
curl 'http://127.0.0.1:8000/devices?status=ONLINE'
```

Fetch the fleet summary:

```bash
curl http://127.0.0.1:8000/summary
```

## Assumptions

- Device ids are unique and limited to simple ASCII-safe characters.
- Heartbeat timestamps are treated as UTC when a timezone is omitted.
- The store is in-memory only, so data is lost when the process restarts.

## Known Limitations

- There is no persistent database.
- Authentication and authorization are out of scope.
- The simulator talks to a single local API instance.
- The project is sized for the requested grading contract rather than production scale.

## What I'd Improve With One More Day

- Add persistent storage.
- Add OpenAPI examples and a small web dashboard.
- Add more simulator presets and richer device telemetry.
- Add a background scheduler so the simulator can report aggregate health.

## AI Usage

I used GitHub Copilot to scaffold the repository, implement the service layers, add tests, and draft this documentation. I reviewed and verified the resulting code and behavior locally.
