from datetime import date

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.weather_agent import run_temperature_outfit_agent, run_weather_outfit_agent

app = FastAPI(
    title="Weather Outfit Agent",
    description="Mini app that calls real weather tools and recommends an outfit.",
    version="0.1.0",
)


class WeatherOutfitAgentRequest(BaseModel):
    city: str
    date: str


class TemperatureOutfitRequest(BaseModel):
    temperature_c: float
    context: str = "hằng ngày"
    location: str = "địa điểm hiện tại"
    date_text: str = "hôm nay"
    rain_probability: float = 0


class TemperatureRange(BaseModel):
    min: float
    max: float


class WeatherSummary(BaseModel):
    city: str
    date: str
    temperature_c: TemperatureRange
    rain_probability: float


class TemperatureOutfitInput(BaseModel):
    temperature_c: float
    context: str
    location: str
    date_text: str
    rain_probability: float


class ToolTraceItem(BaseModel):
    tool: str
    args: dict
    observation: str


class WeatherOutfitAgentResponse(BaseModel):
    finalAnswer: str
    weather: WeatherSummary
    outfitRecommendation: str
    toolTrace: list[ToolTraceItem]


class TemperatureOutfitResponse(BaseModel):
    finalAnswer: str
    input: TemperatureOutfitInput
    outfitRecommendation: str
    toolTrace: list[ToolTraceItem]


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "weather-outfit-agent"}


@app.get("/", response_class=HTMLResponse)
def homepage() -> str:
    return """
<!doctype html>
<html lang="vi">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Weather Outfit Agent</title>
    <style>
      :root {
        color-scheme: light;
        font-family: Arial, sans-serif;
        background: #f6f7f9;
        color: #1f2933;
      }
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
      }
      main {
        width: min(100%, 640px);
        background: white;
        border: 1px solid #d8dee6;
        border-radius: 8px;
        padding: 24px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
      }
      h1 {
        margin: 0 0 20px;
        font-size: 28px;
      }
      label {
        display: grid;
        gap: 8px;
        margin-bottom: 14px;
        font-weight: 700;
      }
      input,
      select {
        min-height: 42px;
        border: 1px solid #b7c1cc;
        border-radius: 6px;
        padding: 0 12px;
        font: inherit;
      }
      button {
        min-height: 44px;
        border: 0;
        border-radius: 6px;
        padding: 0 16px;
        background: #0f766e;
        color: white;
        font: inherit;
        font-weight: 700;
        cursor: pointer;
      }
      pre {
        white-space: pre-wrap;
        overflow-wrap: anywhere;
        margin: 18px 0 0;
        padding: 14px;
        border-radius: 6px;
        background: #edf2f7;
      }
    </style>
  </head>
  <body>
    <main>
      <h1>Weather Outfit Agent</h1>
      <form id="outfit-form">
        <label>
          Địa danh
          <select name="location_choice" id="location-choice">
            <option value="Hà Nội">Hà Nội</option>
            <option value="TP. Hồ Chí Minh">TP. Hồ Chí Minh</option>
            <option value="Đà Nẵng">Đà Nẵng</option>
            <option value="Đà Lạt">Đà Lạt</option>
            <option value="Huế">Huế</option>
            <option value="Cần Thơ">Cần Thơ</option>
            <option value="custom">Khác / tự nhập</option>
          </select>
          <input name="custom_location" id="custom-location" type="text" placeholder="Nhập địa danh khác">
        </label>
        <label>
          Ngày / thời điểm
          <input name="date_text" type="text" value="Thứ 2 ngày 01/06/2026" required>
        </label>
        <label>
          Nhiệt độ hôm nay (°C)
          <input name="temperature_c" type="number" step="0.1" value="36" required>
        </label>
        <label>
          Ngữ cảnh
          <select name="context_choice" id="context-choice">
            <option value="Văn phòng">Văn phòng</option>
            <option value="Sinh viên / đi học">Sinh viên / đi học</option>
            <option value="Đi chơi">Đi chơi</option>
            <option value="Sự kiện lịch sự">Sự kiện lịch sự</option>
            <option value="Du lịch">Du lịch</option>
            <option value="custom">Khác / tự nhập</option>
          </select>
          <input name="custom_context" id="custom-context" type="text" placeholder="Nhập ngữ cảnh khác">
        </label>
        <label>
          Khả năng mưa (0 đến 1)
          <input name="rain_probability" type="number" min="0" max="1" step="0.1" value="0.2">
        </label>
        <button type="submit">Nhận gợi ý outfit</button>
      </form>
      <pre id="result">Nhập thông tin và bấm nút để test.</pre>
    </main>
    <script>
      const form = document.querySelector("#outfit-form");
      const result = document.querySelector("#result");
      const locationChoice = document.querySelector("#location-choice");
      const customLocation = document.querySelector("#custom-location");
      const contextChoice = document.querySelector("#context-choice");
      const customContext = document.querySelector("#custom-context");

      const syncCustomInputs = () => {
        customLocation.hidden = locationChoice.value !== "custom";
        customContext.hidden = contextChoice.value !== "custom";
      };

      locationChoice.addEventListener("change", syncCustomInputs);
      contextChoice.addEventListener("change", syncCustomInputs);
      syncCustomInputs();

      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        result.textContent = "Đang tư vấn...";

        const data = new FormData(form);
        const selectedLocation = String(data.get("location_choice") || "Hà Nội");
        const selectedContext = String(data.get("context_choice") || "Văn phòng");
        const payload = {
          location: selectedLocation === "custom"
            ? String(data.get("custom_location") || "địa điểm hiện tại")
            : selectedLocation,
          date_text: String(data.get("date_text") || "hôm nay"),
          temperature_c: Number(data.get("temperature_c")),
          context: selectedContext === "custom"
            ? String(data.get("custom_context") || "hằng ngày")
            : selectedContext,
          rain_probability: Number(data.get("rain_probability") || 0),
        };

        const response = await fetch("/outfit-recommendation", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payload),
        });
        const body = await response.json();
        result.textContent = response.ok ? body.finalAnswer : JSON.stringify(body, null, 2);
      });
    </script>
  </body>
</html>
"""


@app.post("/weather-outfit-agent", response_model=WeatherOutfitAgentResponse)
def create_weather_outfit_recommendation(request: WeatherOutfitAgentRequest) -> dict:
    try:
        target_date = date.fromisoformat(request.date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Date must use YYYY-MM-DD format.",
        ) from exc

    return run_weather_outfit_agent(city=request.city, target_date=target_date)


@app.post("/outfit-recommendation", response_model=TemperatureOutfitResponse)
def create_direct_outfit_recommendation(request: TemperatureOutfitRequest) -> dict:
    return run_temperature_outfit_agent(
        temperature_c=request.temperature_c,
        context=request.context,
        location=request.location,
        date_text=request.date_text,
        rain_probability=request.rain_probability,
    )
