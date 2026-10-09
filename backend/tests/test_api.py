import pytest
from datetime import date, timedelta
from starlette.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_parse_endpoint():
    resp = client.post("/api/parse", json={"query": "cheap 2-3 night trip, leave Fri or Sat, next 3 months"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_nights"] == 2
    assert data["max_nights"] == 3
    assert set(data["departure_weekdays"]) == {4, 5}
    assert data["allow_open_jaw"] is True
    assert set(data["origins"]) == {"BUD", "DEB", "BTS"}


def test_api_settings_get_and_put():
    # 1. Get settings
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    settings = resp.json()
    assert "BUD-BTS" in settings["ground_transfers"]
    assert settings["ground_transfers"]["BUD-BTS"]["cost_eur"] == 15.0

    # 2. Update settings
    settings["ground_transfers"]["BUD-BTS"]["cost_eur"] = 18.0
    put_resp = client.put("/api/settings", json=settings)
    assert put_resp.status_code == 200
    assert put_resp.json()["ground_transfers"]["BUD-BTS"]["cost_eur"] == 18.0

    # Reset back to 15.0
    settings["ground_transfers"]["BUD-BTS"]["cost_eur"] = 15.0
    client.put("/api/settings", json=settings)


def test_api_search_endpoint_with_mock_params():
    today = date.today()
    params = {
        "origins": ["BUD", "BTS"],
        "destination": "London",
        "date_from": (today + timedelta(days=14)).isoformat(),
        "date_to": (today + timedelta(days=35)).isoformat(),
        "min_nights": 2,
        "max_nights": 3,
        "departure_weekdays": [4, 5],
        "allow_open_jaw": True,
        "currency": "EUR",
        "airlines": ["W6", "FR"]
    }
    resp = client.post("/api/search", json=params)
    assert resp.status_code == 200
    data = resp.json()
    assert "itineraries" in data
    assert "total_results" in data
    assert isinstance(data["itineraries"], list)


def test_api_cache_clear():
    resp = client.post("/api/cache/clear")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
