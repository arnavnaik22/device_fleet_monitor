from __future__ import annotations


def register_and_heartbeat(client, timestamp: str = "2026-01-01T12:00:00Z") -> None:
    assert client.post("/devices", json={"id": "device-01", "name": "Lab Device 01"}).status_code == 201
    assert (
        client.post(
            "/devices/device-01/heartbeat",
            json={"timestamp": timestamp, "status": "OK"},
        ).status_code
        == 202
    )


def test_never_heartbeated_device_is_offline(client) -> None:
    assert client.post("/devices", json={"id": "device-01", "name": "Lab Device 01"}).status_code == 201
    assert client.get("/devices/device-01").json()["status"] == "OFFLINE"


def test_device_is_online_immediately_after_heartbeat(client) -> None:
    register_and_heartbeat(client)
    assert client.get("/devices/device-01").json()["status"] == "ONLINE"


def test_device_stays_online_at_twenty_nine_seconds(client, fake_clock) -> None:
    register_and_heartbeat(client)
    fake_clock.advance(29)
    assert client.get("/devices/device-01").json()["status"] == "ONLINE"


def test_device_stays_online_at_exactly_thirty_seconds(client, fake_clock) -> None:
    register_and_heartbeat(client)
    fake_clock.advance(30)
    assert client.get("/devices/device-01").json()["status"] == "ONLINE"


def test_device_turns_offline_just_over_thirty_seconds(client, fake_clock) -> None:
    register_and_heartbeat(client)
    fake_clock.advance(30.001)
    assert client.get("/devices/device-01").json()["status"] == "OFFLINE"


def test_device_turns_offline_at_thirty_one_seconds(client, fake_clock) -> None:
    register_and_heartbeat(client)
    fake_clock.advance(31)
    assert client.get("/devices/device-01").json()["status"] == "OFFLINE"


def test_heartbeat_after_offline_brings_device_back_online(client, fake_clock) -> None:
    register_and_heartbeat(client)
    fake_clock.advance(31)
    assert client.get("/devices/device-01").json()["status"] == "OFFLINE"
    assert client.post(
        "/devices/device-01/heartbeat",
        json={"timestamp": "2026-01-01T12:00:31Z", "status": "OK"},
    ).status_code == 202
    assert client.get("/devices/device-01").json()["status"] == "ONLINE"


def test_new_heartbeat_resets_timer(client, fake_clock) -> None:
    assert client.post("/devices", json={"id": "device-01", "name": "Lab Device 01"}).status_code == 201
    assert client.post(
        "/devices/device-01/heartbeat",
        json={"timestamp": "2026-01-01T12:00:00Z", "status": "OK"},
    ).status_code == 202
    fake_clock.advance(20)
    assert client.post(
        "/devices/device-01/heartbeat",
        json={"timestamp": "2026-01-01T12:00:20Z", "status": "OK"},
    ).status_code == 202
    fake_clock.advance(29)
    assert client.get("/devices/device-01").json()["status"] == "ONLINE"
    fake_clock.advance(2)
    assert client.get("/devices/device-01").json()["status"] == "OFFLINE"


def test_timeout_is_configurable(fake_clock) -> None:
    from fastapi.testclient import TestClient
    from fleet_monitor.api import create_app

    with TestClient(create_app(clock=fake_clock, timeout=5)) as api_client:
        assert api_client.post("/devices", json={"id": "device-01", "name": "Lab Device 01"}).status_code == 201
        assert api_client.post(
            "/devices/device-01/heartbeat",
            json={"timestamp": "2026-01-01T12:00:00Z", "status": "OK"},
        ).status_code == 202
        fake_clock.advance(5)
        assert api_client.get("/devices/device-01").json()["status"] == "ONLINE"
        fake_clock.advance(0.001)
        assert api_client.get("/devices/device-01").json()["status"] == "OFFLINE"


def test_status_is_reflected_consistently_across_get_list_and_summary(client, fake_clock) -> None:
    assert client.post("/devices", json={"id": "device-01", "name": "Lab Device 01"}).status_code == 201
    assert client.post("/devices", json={"id": "device-02", "name": "Lab Device 02"}).status_code == 201
    assert client.post(
        "/devices/device-01/heartbeat",
        json={"timestamp": "2026-01-01T12:00:00Z", "status": "OK"},
    ).status_code == 202
    fake_clock.advance(31)

    assert client.get("/devices/device-01").json()["status"] == "OFFLINE"
    listing = client.get("/devices").json()
    assert [item["status"] for item in listing] == ["OFFLINE", "OFFLINE"]
    assert client.get("/summary").json() == {"total": 2, "online": 0, "offline": 2}
