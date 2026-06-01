from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import HTTPException, status

FetchJson = Callable[[str, dict[str, str]], dict[str, Any]]

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_json(url: str, params: dict[str, str]) -> dict[str, Any]:
    request_url = f"{url}?{urlencode(params)}"
    try:
        with urlopen(request_url, timeout=10) as response:
            import json

            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Weather provider is unavailable. Please try again later.",
        ) from exc


def recommend_outfit(temp_high: float, rain_probability: float, context: str | None = None) -> str:
    if rain_probability > 0.5:
        recommendation = "Ao mua mong, giay de kho, mang theo o gap."
    elif temp_high > 30:
        recommendation = "Ao nhe, thoang, uu tien vai cotton va mang nuoc."
    elif temp_high < 20:
        recommendation = "Ao dai tay, quan dai va ao khoac nhe de giu am."
    else:
        recommendation = "Trang phuc thoai mai, co the mang ao khoac nhe."

    clean_context = context.strip() if context else ""
    if clean_context:
        return f"{recommendation} Phu hop cho {clean_context}."

    return recommendation


def run_temperature_outfit_agent(
    temperature_c: float,
    context: str = "hang ngay",
    rain_probability: float = 0,
) -> dict[str, Any]:
    temperature = float(temperature_c)
    rain_chance = float(rain_probability)
    clean_context = context.strip() or "hang ngay"

    if temperature < -30 or temperature > 55:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Temperature must be between -30 and 55°C.",
        )
    if rain_chance < 0 or rain_chance > 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Rain probability must be between 0 and 1.",
        )

    recommendation = recommend_outfit(temperature, rain_chance, clean_context)
    rain_percent = round(rain_chance * 100)

    return {
        "finalAnswer": (
            f"Hom nay {temperature:g}°C, ngu canh {clean_context}, "
            f"kha nang mua {rain_percent}%. Goi y: {recommendation}"
        ),
        "input": {
            "temperature_c": temperature,
            "context": clean_context,
            "rain_probability": rain_chance,
        },
        "outfitRecommendation": recommendation,
        "toolTrace": [
            {
                "tool": "read_temperature_input",
                "args": {
                    "temperature_c": temperature,
                    "context": clean_context,
                    "rain_probability": rain_chance,
                },
                "observation": f"temp={temperature:g}C, context={clean_context}, rain_probability={rain_chance:g}",
            },
            {
                "tool": "recommend_outfit",
                "args": {
                    "temp_high": temperature,
                    "rain_probability": rain_chance,
                    "context": clean_context,
                },
                "observation": recommendation,
            },
        ],
    }


def run_weather_outfit_agent(
    city: str,
    target_date: date,
    fetch_json: FetchJson = fetch_json,
) -> dict[str, Any]:
    clean_city = city.strip()
    if not clean_city:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="City must not be empty.",
        )

    geocoding_payload = fetch_json(
        GEOCODING_URL,
        {
            "name": clean_city,
            "count": "1",
            "language": "vi",
            "format": "json",
        },
    )
    locations = geocoding_payload.get("results") or []
    if not locations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find coordinates for this city.",
        )

    location = locations[0]
    resolved_city = location.get("name") or clean_city
    latitude = location["latitude"]
    longitude = location["longitude"]
    date_text = target_date.isoformat()

    forecast_payload = fetch_json(
        FORECAST_URL,
        {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "start_date": date_text,
            "end_date": date_text,
        },
    )
    daily = forecast_payload.get("daily") or {}
    try:
        temp_min = float(daily["temperature_2m_min"][0])
        temp_max = float(daily["temperature_2m_max"][0])
        rain_probability = float(daily["precipitation_probability_max"][0]) / 100
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Weather provider returned an unexpected forecast payload.",
        ) from exc

    recommendation = recommend_outfit(temp_max, rain_probability)
    rain_percent = round(rain_probability * 100)

    return {
        "finalAnswer": (
            f"Thoi tiet o {resolved_city} ngay {date_text}: "
            f"{temp_min:g}-{temp_max:g}°C, kha nang mua {rain_percent}%. "
            f"Goi y: {recommendation}"
        ),
        "weather": {
            "city": resolved_city,
            "date": date_text,
            "temperature_c": {"min": temp_min, "max": temp_max},
            "rain_probability": rain_probability,
        },
        "outfitRecommendation": recommendation,
        "toolTrace": [
            {
                "tool": "geocode_city",
                "args": {"city": clean_city},
                "observation": f"{resolved_city} -> lat={latitude}, lon={longitude}",
            },
            {
                "tool": "get_weather",
                "args": {"city": resolved_city, "date": date_text},
                "observation": f"temp={temp_min:g}-{temp_max:g}C, rain_probability={rain_probability:g}",
            },
            {
                "tool": "recommend_outfit",
                "args": {"temp_high": temp_max, "rain_probability": rain_probability},
                "observation": recommendation,
            },
        ],
    }
