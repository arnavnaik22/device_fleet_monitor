from __future__ import annotations


def register_device(client, device_id: str = "device-01") -> None:
    response = client.post("/devices", json={"id": device_id, "name": "Lab Device 01"})
    assert response.status_code == 201


def test_valid_heartbeat_makes_device_online(client) -> None:
    register_device(client)

    response = client.post(
        "/devices/device-01/heartbeat",
        json={
            "timestamp": "2026-09-21T10:30:00Z",
            "status": "OK",
            "cpu_usage": 42,
            "signal_strength": -71,
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "id": "device-01",
        "status": "ONLINE",
        "last_heartbeat": "2026-09-21T10:30:00Z",
    }


def test_unknown_device_heartbeat_returns_not_found(client) -> None:
    response = client.post(
        "/devices/missing/heartbeat",
        json={"status": "OK"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Device 'missing' not found"}


def test_invalid_heartbeat_fields_return_validation_errors(client) -> None:
    register_device(client)

    assert (
        client.post(
            "/devices/device-01/heartbeat",
            json={"timestamp": "2026-09-21T10:30:00Z", "status": "bad"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/devices/device-01/heartbeat",
            json={"timestamp": "not-a-datetime", "status": "OK"},
        ).status_code
        == 422
    )


def test_missing_timestamp_uses_server_time(client) -> None:
    register_device(client)

    response = client.post("/devices/device-01/heartbeat", json={"status": "OK"})

    assert response.status_code == 202
    assert response.json()["last_heartbeat"] == "2026-01-01T12:00:00Z"


def test_naive_timestamp_is_treated_as_utc(client) -> None:
    register_device(client)

    response = client.post(
        "/devices/device-01/heartbeat",
        json={"timestamp": "2026-09-21T10:30:00", "status": "OK"},
    )

    assert response.status_code == 202
    assert response.json()["last_heartbeat"] == "2026-09-21T10:30:00Z"


def test_cpu_usage_out_of_range_returns_validation_error(client) -> None:
    register_device(client)

    response = client.post(
        "/devices/device-01/heartbeat",
        json={"status": "OK", "cpu_usage": 101},
    )

    assert response.status_code == 422


def test_optional_metrics_are_stored_and_returned(client) -> None:
    register_device(client)

    response = client.post(
        "/devices/device-01/heartbeat",
        json={"status": "DEGRADED", "cpu_usage": 55.5, "signal_strength": -77},
    )

    assert response.status_code == 202
    details = client.get("/devices/device-01").json()
    assert details["reported_status"] == "DEGRADED"
    assert details["cpu_usage"] == 55.5
    assert details["signal_strength"] == -77


def test_out_of_order_heartbeat_keeps_latest_timestamp_but_refreshes_liveness(client, fake_clock) -> None:
    register_device(client)

    assert (
        client.post(
            "/devices/device-01/heartbeat",
            json={"timestamp": "2026-01-01T12:00:10Z", "status": "OK"},
        ).status_code
        == 202
    )
    fake_clock.advance(10)
    assert (
        client.post(
            "/devices/device-01/heartbeat",
            json={"timestamp": "2026-01-01T12:00:05Z", "status": "DEGRADED"},
        ).status_code
        == 202
    )

    details = client.get("/devices/device-01").json()
    assert details["last_heartbeat"] == "2026-01-01T12:00:10Z"
    assert details["last_seen_at"] == "2026-01-01T12:00:10Z"
    assert details["reported_status"] == "OK"
