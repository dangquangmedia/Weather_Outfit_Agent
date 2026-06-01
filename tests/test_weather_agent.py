from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.weather_agent import run_temperature_outfit_agent, run_weather_outfit_agent


def test_weather_agent_uses_tools_and_recommends_rain_outfit() -> None:
    calls: list[str] = []

    def fake_fetch_json(url: str, params: dict[str, str]) -> dict:
        calls.append(url)
        if "geocoding-api" in url:
            return {
                "results": [
                    {
                        "name": "Ho Chi Minh City",
                        "country": "Vietnam",
                        "latitude": 10.8231,
                        "longitude": 106.6297,
                    }
                ]
            }
        return {
            "daily": {
                "time": ["2026-06-02"],
                "temperature_2m_min": [27.0],
                "temperature_2m_max": [32.0],
                "precipitation_probability_max": [70],
            }
        }

    result = run_weather_outfit_agent(
        city="Ho Chi Minh City",
        target_date=date(2026, 6, 2),
        fetch_json=fake_fetch_json,
    )

    assert calls == [
        "https://geocoding-api.open-meteo.com/v1/search",
        "https://api.open-meteo.com/v1/forecast",
    ]
    assert result["weather"]["temperature_c"] == {"min": 27.0, "max": 32.0}
    assert result["weather"]["rain_probability"] == 0.7
    assert "áo mưa" in result["outfitRecommendation"].lower()
    assert [step["tool"] for step in result["toolTrace"]] == ["geocode_city", "get_weather", "recommend_outfit"]


def test_weather_agent_endpoint_returns_tool_trace(monkeypatch) -> None:
    def fake_agent(city: str, target_date: date) -> dict:
        return {
            "finalAnswer": f"Thoi tiet o {city} ngay {target_date.isoformat()} co mua.",
            "weather": {
                "city": city,
                "date": target_date.isoformat(),
                "temperature_c": {"min": 26.0, "max": 31.0},
                "rain_probability": 0.65,
            },
            "outfitRecommendation": "Áo mưa mỏng, giày dễ khô, mang theo ô gấp.",
            "toolTrace": [
                {
                    "tool": "get_weather",
                    "args": {"city": city, "date": target_date.isoformat()},
                    "observation": "rain_probability=0.65",
                }
            ],
        }

    monkeypatch.setattr("app.main.run_weather_outfit_agent", fake_agent)
    client = TestClient(app)

    response = client.post(
        "/weather-outfit-agent",
        json={"city": "Da Nang", "date": "2026-06-03"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["weather"]["city"] == "Da Nang"
    assert body["outfitRecommendation"] == "Áo mưa mỏng, giày dễ khô, mang theo ô gấp."
    assert body["toolTrace"][0]["tool"] == "get_weather"


def test_temperature_outfit_agent_recommends_for_direct_temperature_input() -> None:
    result = run_temperature_outfit_agent(
        temperature_c=36,
        context="đi học",
        location="Hà Nội",
        date_text="Thứ 2 ngày 01/06/2026",
        rain_probability=0.2,
    )

    assert result["input"] == {
        "temperature_c": 36.0,
        "context": "đi học",
        "location": "Hà Nội",
        "date_text": "Thứ 2 ngày 01/06/2026",
        "rain_probability": 0.2,
    }
    assert "Thứ 2 ngày 01/06/2026 tại Hà Nội" in result["finalAnswer"]
    assert "36°C" in result["finalAnswer"]
    assert "Áo thun cotton sáng màu" in result["outfitRecommendation"]
    assert [step["tool"] for step in result["toolTrace"]] == ["read_temperature_input", "recommend_outfit"]


def test_temperature_outfit_endpoint_returns_direct_recommendation() -> None:
    client = TestClient(app)

    response = client.post(
        "/outfit-recommendation",
        json={
            "location": "Hà Nội",
            "date_text": "Thứ 2 ngày 01/06/2026",
            "temperature_c": 36,
            "context": "đi học",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["input"]["location"] == "Hà Nội"
    assert body["input"]["date_text"] == "Thứ 2 ngày 01/06/2026"
    assert body["input"]["temperature_c"] == 36.0
    assert body["input"]["context"] == "đi học"
    assert "Hà Nội" in body["finalAnswer"]
    assert "Áo thun cotton sáng màu" in body["outfitRecommendation"]
    assert body["toolTrace"][0]["tool"] == "read_temperature_input"


def test_homepage_has_direct_temperature_input_form() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert 'name="location"' in response.text
    assert 'name="date_text"' in response.text
    assert 'name="temperature_c"' in response.text
    assert "Hà Nội" in response.text
    assert "/outfit-recommendation" in response.text
