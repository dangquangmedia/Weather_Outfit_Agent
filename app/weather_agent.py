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

LOCATION_STYLE_NOTES = {
    "hà nội": "Vì ở Hà Nội, ưu tiên nét lịch sự, gọn gàng và kín đáo vừa phải.",
    "tp. hồ chí minh": "Vì ở TP. Hồ Chí Minh, ưu tiên chất liệu nhẹ, thoáng và năng động.",
    "thành phố hồ chí minh": "Vì ở TP. Hồ Chí Minh, ưu tiên chất liệu nhẹ, thoáng và năng động.",
    "đà nẵng": "Vì ở Đà Nẵng, ưu tiên trang phục thoáng, dễ di chuyển và hợp không khí biển.",
    "đà lạt": "Vì ở Đà Lạt, nên mặc nhiều lớp mỏng để dễ thích nghi khi trời se lạnh.",
    "huế": "Vì ở Huế, ưu tiên phong cách nhã nhặn, kín đáo và màu sắc nhẹ.",
    "cần thơ": "Vì ở Cần Thơ, ưu tiên đồ thoáng mát, mềm nhẹ và tiện di chuyển.",
}


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


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def recommend_outfit(
    temp_high: float,
    rain_probability: float,
    context: str | None = None,
    location: str | None = None,
) -> str:
    clean_context = context.strip() if context else ""
    clean_location = location.strip() if location else ""
    context_key = clean_context.lower()
    location_key = clean_location.lower()

    if rain_probability > 0.5:
        recommendation = "Áo mưa mỏng, giày dễ khô, mang theo ô gấp."
    elif _contains_any(context_key, ("văn phòng", "office", "đi làm", "cong so", "công sở")):
        if temp_high > 30:
            recommendation = "Sơ mi linen hoặc polo sáng màu, quần chinos mỏng, giày loafer hoặc sneaker tối giản."
        elif temp_high < 20:
            recommendation = "Sơ mi dài tay, blazer mỏng, quần âu và giày kín."
        else:
            recommendation = "Sơ mi hoặc polo gọn gàng, quần âu/chinos và giày kín lịch sự."
    elif _contains_any(context_key, ("sinh viên", "đi học", "student", "học")):
        if temp_high > 30:
            recommendation = "Áo thun cotton hoặc polo thoáng, quần jeans mỏng/kaki, sneaker nhẹ và bình nước."
        elif temp_high < 20:
            recommendation = "Áo hoodie hoặc cardigan mỏng, quần jeans và sneaker."
        else:
            recommendation = "Áo thun hoặc polo, quần jeans/kaki và sneaker thoải mái."
    elif _contains_any(context_key, ("sự kiện", "lịch sự", "formal", "tiệc")):
        if temp_high > 30:
            recommendation = "Sơ mi linen, quần tây mỏng hoặc váy thanh lịch chất liệu nhẹ, giày kín thoáng."
        else:
            recommendation = "Sơ mi/blazer nhẹ hoặc váy thanh lịch, phối giày kín gọn gàng."
    elif _contains_any(context_key, ("du lịch", "đi chơi", "travel", "chơi")):
        if temp_high > 30:
            recommendation = "Áo thun thoáng, quần short hoặc quần suông nhẹ, sandal/sneaker và mũ chống nắng."
        else:
            recommendation = "Áo thun hoặc sơ mi khoác ngoài, quần thoải mái và giày dễ đi bộ."
    elif temp_high > 30:
        recommendation = "Áo thun cotton sáng màu, quần vải mỏng, giày thoáng và mang theo nước."
    elif temp_high < 20:
        recommendation = "Áo dài tay, quần dài và áo khoác nhẹ để giữ ấm."
    else:
        recommendation = "Trang phục thoải mái, có thể mang áo khoác nhẹ."

    location_note = LOCATION_STYLE_NOTES.get(location_key)
    if not location_note and clean_location:
        location_note = f"Vì ở {clean_location}, nên ưu tiên trang phục phù hợp văn hóa địa phương và lịch trình trong ngày."

    details = []
    if clean_context:
        details.append(f"Phù hợp cho {clean_context}.")
    if clean_location and location_note:
        details.append(location_note)

    return " ".join([recommendation, *details])


def run_temperature_outfit_agent(
    temperature_c: float,
    context: str = "hang ngay",
    location: str = "địa điểm hiện tại",
    date_text: str = "hôm nay",
    rain_probability: float = 0,
) -> dict[str, Any]:
    temperature = float(temperature_c)
    rain_chance = float(rain_probability)
    clean_context = context.strip() or "hằng ngày"
    clean_location = location.strip() or "địa điểm hiện tại"
    clean_date_text = date_text.strip() or "hôm nay"

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

    recommendation = recommend_outfit(temperature, rain_chance, clean_context, clean_location)
    rain_percent = round(rain_chance * 100)

    return {
        "finalAnswer": (
            f"Hôm nay {clean_date_text} tại {clean_location}, nhiệt độ {temperature:g}°C, "
            f"ngữ cảnh {clean_context}, khả năng mưa {rain_percent}%. Gợi ý: {recommendation}"
        ),
        "input": {
            "temperature_c": temperature,
            "context": clean_context,
            "location": clean_location,
            "date_text": clean_date_text,
            "rain_probability": rain_chance,
        },
        "outfitRecommendation": recommendation,
        "toolTrace": [
            {
                "tool": "read_temperature_input",
                "args": {
                    "temperature_c": temperature,
                    "context": clean_context,
                    "location": clean_location,
                    "date_text": clean_date_text,
                    "rain_probability": rain_chance,
                },
                "observation": (
                    f"location={clean_location}, date={clean_date_text}, "
                    f"temp={temperature:g}C, context={clean_context}, rain_probability={rain_chance:g}"
                ),
            },
            {
                "tool": "recommend_outfit",
                "args": {
                    "temp_high": temperature,
                    "rain_probability": rain_chance,
                    "context": clean_context,
                    "location": clean_location,
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
