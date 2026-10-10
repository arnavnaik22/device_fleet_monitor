# Mini Device Fleet Monitor

A small FastAPI service for tracking registered devices, their latest heartbeat, and a derived online/offline status based on a 30-second timeout.

---

## What The Project Does

The service allows you to:

* register devices
* accept heartbeat payloads with status, CPU usage, and signal strength
* derive `ONLINE` / `OFFLINE` from the server-side receipt time
* list devices and inspect a per-device record
* fetch a fleet summary from `GET /summary`
* run a simple multi-device simulator against the API

The liveness rule is simple: a device is `ONLINE` when its last heartbeat was accepted within the last 30 seconds; otherwise it is `OFFLINE`.

---

## Design / Architecture

The service keeps the status calculation in one place and evaluates it when a request is made instead of updating a background field.

```text
       [ Device Clients / Simulator ]
                       │
                 HTTP JSON
                       ▼
    ┌──────────────────────────────────────┐
    │          api.py (FastAPI)            │
    │  routes, validation, response shapes │
    └──────────────────┬───────────────────┘
                       │ calls
    ┌──────────────────▼───────────────────┐
    │             service.py                │
    │ registration and heartbeat logic     │
    └──────────┬─────────────────┬─────────┘
               │                 │
    ┌──────────▼──────┐  ┌────────▼──────────┐
    │     store.py    │  │    domain.py      │
    │ in-memory store │  │ compute_status()  │
    │ + lock          │  │ last_seen_at + now│
    └─────────────────┘  └───────────────────┘
```

### Key design decisions

* Read-time evaluation: `status = ONLINE if now - last_seen_at <= 30s else OFFLINE`.
* Server-authoritative time: `last_seen_at` is set on server receipt, not on the device timestamp.
* Injectable clock: the app accepts a clock for deterministic tests without `time.sleep()`.
* Thread-safe storage: the device store uses a `threading.Lock` to guard in-memory state.

---

## Repository Structure

```text
device_fleet_monitor/
├── README.md
├── requirements.txt
├── pytest.ini
├── src/
│   └── fleet_monitor/
│       ├── __init__.py
│       ├── api.py
│       ├── clock.py
│       ├── config.py
│       ├── domain.py
│       ├── errors.py
│       ├── models.py
│       ├── service.py
│       └── store.py
├── simulator/
│   └── simulate.py
├── tests/
│   ├── conftest.py
│   ├── test_concurrency.py
│   ├── test_domain.py
│   ├── test_heartbeat.py
│   ├── test_listing_summary.py
│   ├── test_registration.py
│   ├── test_status_timeout.py
│   └── test_validation.py
└── .gitignore
```

---

## Prerequisites

* Python 3.11+
* pip
* a virtual environment

On Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

---

## Build & Installation

```bash
git clone https://github.com/arnavnaik22/device_fleet_monitor.git
cd device_fleet_monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Run The Application

Start the API before any simulator traffic:

```bash
uvicorn --app-dir src fleet_monitor.api:app --host 127.0.0.1 --port 8000 --reload
```

The OpenAPI docs are available at http://127.0.0.1:8000/docs.

### Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `HEARTBEAT_TIMEOUT_SECONDS` | `30` | Timeout cutoff for ONLINE/OFFLINE |
| `HOST` | `127.0.0.1` | Bind address |
| `PORT` | `8000` | Bind port |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Run The Simulator

The simulator registers a small fleet and sends heartbeats on a loop.

```bash
python simulator/simulate.py --devices 5 --interval 5
```

The server must already be running before you start the simulator.

Interactive controls while it is running:

* `stop device-03` stops that device's heartbeat loop
* `start device-03` resumes it
* `quit` exits the simulator

For non-interactive use, `--stop-after device-03:20` will stop a device after 20 seconds.

Expected observation: after `stop device-03`, wait around 30 seconds and run `curl http://127.0.0.1:8000/summary`; you should see `4 online` and `1 offline`.

---

## Run The Tests

```bash
pytest -q
```

The repository currently includes 36 tests, and they pass in about 0.7s in this environment.

---

## Example API Requests

Expected status codes: `201`, `202`, `404`, `409`, and `422`.

### Register a device

```bash
curl -X POST http://127.0.0.1:8000/devices \
  -H "Content-Type: application/json" \
  -d '{"id":"device-01","name":"Lab Device 01"}'
```

Response:

```json
{
  "id": "device-01",
  "name": "Lab Device 01",
  "status": "OFFLINE",
  "last_heartbeat": null
}
```

### Send a heartbeat

```bash
curl -X POST http://127.0.0.1:8000/devices/device-01/heartbeat \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-10-10T08:30:00Z",
    "status": "OK",
    "cpu_usage": 42.5,
    "signal_strength": -68
  }'
```

Response:

```json
{
  "id": "device-01",
  "status": "ONLINE",
  "last_heartbeat": "2026-10-10T08:30:00Z"
}
```

### Fetch details for one device

```bash
curl http://127.0.0.1:8000/devices/device-01
```

### List devices with a status filter

```bash
curl "http://127.0.0.1:8000/devices?status=ONLINE"
```

### Fetch the fleet summary

```bash
curl http://127.0.0.1:8000/summary
```

Example response:

```json
{
  "total": 5,
  "online": 4,
  "offline": 1
}
```

---

## Assumptions

1. Device IDs are unique and limited to alphanumeric characters, dots, dashes, and underscores.
2. The server decides liveness from its own receipt time, not from the device-reported timestamp.
3. If a device has never sent a heartbeat, it starts as `OFFLINE`.
4. A naive timestamp from the client is treated as UTC.
5. Device state is kept in memory only and resets when the process restarts.

---

## Known Limitations

* There is no persistent database.
* Authentication and authorization are out of scope for this exercise.
* The simulator talks to a single local API instance.
* Only the latest heartbeat metrics are retained; there is no history table.

---

## What I'd Improve With One More Day

1. Add persistent storage and historical telemetry queries.
2. Add a small web dashboard or live status view.
3. Add Redis or another shared store for multi-process deployment.
4. Add device authentication and stronger network security.
5. Add Prometheus-style metrics for fleet health and heartbeat latency.

---

## AI Usage

* I used GitHub Copilot Chat and the VS Code agent to scaffold the project, review edge cases, and sanity-check the API contract.
* During schema review, I tightened the initially permissive telemetry validation: `cpu_usage` now rejects non-finite values and must stay within `0` to `100`, while `signal_strength` must stay within `-120` to `0` dBm.

### Personally Verified Deliverables

1. **Automated test regression**: the repo's 36 tests pass in about 0.7s in this environment.
2. **Boundary verification**: exactly 30.000s is `ONLINE`, 30.001s is `OFFLINE`; changing the comparison to `<` caused the boundary check to fail immediately.
3. **Telemetry validation**: invalid `cpu_usage` values such as `NaN` and `Infinity`, and out-of-range `signal_strength` values outside `[-120, 0]`, are rejected with HTTP 422.
4. **Concurrency check**: the repository's concurrency tests cover 50 simultaneous distinct registrations and 20 same-ID registration attempts; the same-ID case yields one successful registration and the rest are 409 conflicts.
5. **Clean-clone reproducibility**: cloning the repo into a temporary directory and installing dependencies followed by `pytest -q` worked without undocumented setup steps.
