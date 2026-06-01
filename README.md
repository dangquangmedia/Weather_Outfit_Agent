# Weather Outfit Agent

Mini app FastAPI demo tool calling:

1. Geocode city with Open-Meteo.
2. Fetch real weather forecast.
3. Recommend an outfit.
4. Return a lesson-friendly `toolTrace`.

It also supports a direct temperature mode for quick outfit advice without
calling the weather provider.

## Run

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000/
```

API docs:

```text
http://localhost:8000/docs
```

## Test input

Real weather endpoint:

```text
POST /weather-outfit-agent
```

Body:

```json
{
  "city": "Ho Chi Minh City",
  "date": "2026-06-01"
}
```

Direct temperature endpoint:

```text
POST /outfit-recommendation
```

Body:

```json
{
  "location": "Hà Nội",
  "date_text": "Thứ 2 ngày 01/06/2026",
  "temperature_c": 36,
  "context": "đi học",
  "rain_probability": 0.2
}
```

Example output:

```text
Hôm nay Thứ 2 ngày 01/06/2026 tại Hà Nội, nhiệt độ 36°C, ngữ cảnh đi học, khả năng mưa 20%.
Gợi ý: Áo thun cotton sáng màu, quần vải mỏng, giày thoáng và mang theo nước. Phù hợp cho đi học.
```

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```
