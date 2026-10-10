from __future__ import annotations


def test_registers_device_as_offline(client) -> None:
    response = client.post("/devices", json={"id": "device-01", "name": "Lab Device 01"})

    assert response.status_code == 201
    assert response.json() == {
        "id": "device-01",
        "name": "Lab Device 01",
        "status": "OFFLINE",
        "last_heartbeat": None,
    }


def test_duplicate_device_id_returns_conflict(client) -> None:
    payload = {"id": "device-01", "name": "Lab Device 01"}
    assert client.post("/devices", json=payload).status_code == 201

    response = client.post("/devices", json=payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "Device 'device-01' already exists"}


def test_invalid_device_ids_return_validation_error(client) -> None:
    for invalid_id in ["with spaces", "", "x" * 65]:
        response = client.post("/devices", json={"id": invalid_id, "name": "Lab Device 01"})
        assert response.status_code == 422


def test_blank_device_names_return_validation_error(client) -> None:
    for invalid_name in ["", "   "]:
        response = client.post("/devices", json={"id": "device-01", "name": invalid_name})
        assert response.status_code == 422


def test_missing_registration_fields_return_validation_error(client) -> None:
    assert client.post("/devices", json={"name": "Lab Device 01"}).status_code == 422
    assert client.post("/devices", json={"id": "device-01"}).status_code == 422
