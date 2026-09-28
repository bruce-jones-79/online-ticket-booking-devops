import pytest
from app import app, init_db


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    init_db()
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_search_booking_and_payment(client):
    response = client.post("/api/trips", json={
        "mode": "FLIGHT",
        "origin": "JAX",
        "destination": "ATL",
        "travel_date": "2026-10-01",
        "available_seats": 1
    })
    assert response.status_code == 201

    trip_id = response.json["trip_id"]

    response = client.get(
        "/api/trips?origin=JAX&destination=ATL&date=2026-10-01&mode=FLIGHT"
    )
    assert response.status_code == 200
    assert len(response.json) == 1

    response = client.post(
        "/api/bookings",
        json={"user_id": 101, "trip_id": trip_id}
    )
    assert response.status_code == 201
    booking_id = response.json["booking_id"]

    response = client.post(
        "/api/payments",
        json={"booking_id": booking_id, "amount": 125.00}
    )
    assert response.status_code == 201
    assert response.json["status"] == "AUTHORIZED"


def test_booking_rejected_when_no_seats(client):
    response = client.post("/api/trips", json={
        "mode": "BUS",
        "origin": "JAX",
        "destination": "ORL",
        "travel_date": "2026-10-02",
        "available_seats": 0
    })
    assert response.status_code == 201

    trip_id = response.json["trip_id"]

    response = client.post(
        "/api/bookings",
        json={"user_id": 1, "trip_id": trip_id}
    )
    assert response.status_code == 409
