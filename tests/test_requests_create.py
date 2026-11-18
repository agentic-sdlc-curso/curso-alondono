from datetime import datetime

import pytest
from fastapi.testclient import TestClient


def test_t1_creates_request_with_generated_fields(client: TestClient) -> None:
    response = client.post(
        "/requests",
        json={"title": "Laptop", "description": "Need a work laptop"},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "title", "description", "status", "created_at"}
    assert body["id"]
    assert body["title"] == "Laptop"
    assert body["description"] == "Need a work laptop"
    assert body["status"] == "open"
    assert isinstance(body["created_at"], str)
    datetime.fromisoformat(body["created_at"].replace("Z", "+00:00"))


def test_t2_missing_title_returns_400_json_error(client: TestClient) -> None:
    response = client.post("/requests", json={"description": "Need access"})

    assert response.status_code == 400
    assert isinstance(response.json().get("error"), str)
    assert response.json()["error"].strip()


def test_t3_missing_description_returns_400_json_error(client: TestClient) -> None:
    response = client.post("/requests", json={"title": "System access"})

    assert response.status_code == 400
    assert isinstance(response.json().get("error"), str)
    assert response.json()["error"].strip()


def test_t4_trims_title_and_description(client: TestClient) -> None:
    response = client.post(
        "/requests",
        json={"title": "  Laptop  ", "description": "  Need a laptop  "},
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Laptop"
    assert response.json()["description"] == "Need a laptop"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", ""),
        ("title", "   "),
        ("description", ""),
        ("description", "   "),
    ],
)
def test_t5_empty_or_whitespace_text_returns_400(
    client: TestClient, field: str, value: str
) -> None:
    payload = {"title": "Laptop", "description": "Need a laptop"}
    payload[field] = value
    response = client.post("/requests", json=payload)

    assert response.status_code == 400
    assert isinstance(response.json().get("error"), str)
    assert response.json()["error"].strip()


def test_t6_accepts_100_character_title_and_rejects_101(
    client: TestClient,
) -> None:
    accepted_title = " " + ("T" * 100) + " "
    accepted = client.post(
        "/requests",
        json={"title": accepted_title, "description": "Description"},
    )
    rejected = client.post(
        "/requests",
        json={"title": "T" * 101, "description": "Description"},
    )

    assert accepted.status_code == 201
    assert accepted.json()["title"] == "T" * 100
    assert rejected.status_code == 400
    assert isinstance(rejected.json().get("error"), str)
    assert rejected.json()["error"].strip()


def test_t7_accepts_1000_character_description_and_rejects_1001(
    client: TestClient,
) -> None:
    accepted_description = " " + ("D" * 1000) + " "
    accepted = client.post(
        "/requests",
        json={"title": "Laptop", "description": accepted_description},
    )
    rejected = client.post(
        "/requests",
        json={"title": "Laptop", "description": "D" * 1001},
    )

    assert accepted.status_code == 201
    assert accepted.json()["description"] == "D" * 1000
    assert rejected.status_code == 400
    assert isinstance(rejected.json().get("error"), str)
    assert rejected.json()["error"].strip()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", 123),
        ("description", 123),
    ],
)
def test_t8_non_text_field_returns_400(
    client: TestClient, field: str, value: object
) -> None:
    payload: dict[str, object] = {
        "title": "Laptop",
        "description": "Need a laptop",
    }
    payload[field] = value
    response = client.post("/requests", json=payload)

    assert response.status_code == 400
    assert isinstance(response.json().get("error"), str)
    assert response.json()["error"].strip()


def test_t8_malformed_json_returns_400_json_error(client: TestClient) -> None:
    response = client.post(
        "/requests",
        content="{ not json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert isinstance(response.json().get("error"), str)
    assert response.json()["error"].strip()


def test_t9_ignores_additional_properties(client: TestClient) -> None:
    response = client.post(
        "/requests",
        json={
            "title": "Laptop",
            "description": "Need a laptop",
            "unexpected": "must not be returned",
        },
    )

    assert response.status_code == 201
    assert "unexpected" not in response.json()


def test_t10_duplicate_requests_receive_distinct_ids(client: TestClient) -> None:
    payload = {"title": "Laptop", "description": "Need a laptop"}

    first = client.post("/requests", json=payload)
    second = client.post("/requests", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
