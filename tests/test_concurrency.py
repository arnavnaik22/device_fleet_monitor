from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor


def test_concurrent_registration_of_distinct_ids(client) -> None:
    def register(index: int) -> int:
        response = client.post(
            "/devices",
            json={"id": f"device-{index:02d}", "name": f"Device {index:02d}"},
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=10) as executor:
        statuses = list(executor.map(register, range(50)))

    assert statuses.count(201) == 50
    assert client.get("/summary").json()["total"] == 50


def test_concurrent_registration_of_same_id_allows_only_one_success(client) -> None:
    def register(_: int) -> int:
        response = client.post(
            "/devices",
            json={"id": "device-01", "name": "Device 01"},
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=10) as executor:
        statuses = list(executor.map(register, range(20)))

    assert statuses.count(201) == 1
    assert statuses.count(409) == 19
