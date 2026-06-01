# Weather Outfit Agent

Mini app FastAPI demo tool calling:

1. Geocode city with Open-Meteo.
2. Fetch real weather forecast.
3. Recommend an outfit.
4. Return a lesson-friendly `toolTrace`.

It also supports a direct temperature mode for quick outfit advice without
calling the weather provider. The direct mode can adjust recommendations by
location culture and activity context.

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
  "context": "Văn phòng",
  "rain_probability": 0.1
}
```

Example output:

```text
Hôm nay Thứ 2 ngày 01/06/2026 tại Hà Nội, nhiệt độ 36°C, ngữ cảnh Văn phòng, khả năng mưa 10%.
Gợi ý: Sơ mi linen hoặc polo sáng màu, quần chinos mỏng, giày loafer hoặc sneaker tối giản. Phù hợp cho Văn phòng. Vì ở Hà Nội, ưu tiên nét lịch sự, gọn gàng và kín đáo vừa phải.
```

The homepage includes dropdowns for common locations and contexts, plus
`Khác / tự nhập` options when you want a custom place or activity.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest
```
