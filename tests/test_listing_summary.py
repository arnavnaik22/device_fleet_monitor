from __future__ import annotations


def test_empty_fleet_returns_empty_list_and_zero_summary(client) -> None:
    assert client.get("/devices").json() == []
    assert client.get("/summary").json() == {"total": 0, "online": 0, "offline": 0}


def test_mixed_fleet_summary_counts_are_consistent(client, fake_clock) -> None:
    client.post("/devices", json={"id": "device-01", "name": "Device 01"})
    client.post("/devices", json={"id": "device-02", "name": "Device 02"})
    client.post("/devices", json={"id": "device-03", "name": "Device 03"})
    client.post(
        "/devices/device-01/heartbeat",
        json={"timestamp": "2026-01-01T12:00:00Z", "status": "OK"},
    )
    client.post(
        "/devices/device-02/heartbeat",
        json={"timestamp": "2026-01-01T12:00:00Z", "status": "OK"},
    )
    fake_clock.advance(31)
    client.post(
        "/devices/device-02/heartbeat",
        json={"timestamp": "2026-01-01T12:00:31Z", "status": "OK"},
    )

    summary = client.get("/summary").json()
    assert summary == {"total": 3, "online": 1, "offline": 2}
    assert summary["total"] == summary["online"] + summary["offline"]


def test_list_is_sorted_by_device_id(client) -> None:
    client.post("/devices", json={"id": "device-03", "name": "Device 03"})
    client.post("/devices", json={"id": "device-01", "name": "Device 01"})
    client.post("/devices", json={"id": "device-02", "name": "Device 02"})

    listing = client.get("/devices").json()
    assert [item["id"] for item in listing] == ["device-01", "device-02", "device-03"]


def test_list_can_filter_by_status_and_reject_invalid_values(client, fake_clock) -> None:
    client.post("/devices", json={"id": "device-01", "name": "Device 01"})
    client.post("/devices", json={"id": "device-02", "name": "Device 02"})
    client.post(
        "/devices/device-01/heartbeat",
        json={"timestamp": "2026-01-01T12:00:00Z", "status": "OK"},
    )
    fake_clock.advance(31)

    online = client.get("/devices?status=ONLINE").json()
    offline = client.get("/devices?status=OFFLINE").json()
    assert [item["id"] for item in online] == []
    assert sorted(item["id"] for item in offline) == ["device-01", "device-02"]
    assert client.get("/devices?status=BAD").status_code == 422


def test_unknown_device_details_returns_not_found(client) -> None:
    response = client.get("/devices/missing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Device 'missing' not found"}
