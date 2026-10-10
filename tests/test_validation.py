from __future__ import annotations


def test_invalid_status_filter_is_rejected(client) -> None:
    assert client.get("/devices?status=UNKNOWN").status_code == 422
