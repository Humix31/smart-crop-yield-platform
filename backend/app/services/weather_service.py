import logging
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _demo_weather(district: str, message: str, reason: str) -> dict:
    return {
        "district": district,
        "temperature": 29.5,
        "humidity": 68,
        "wind": 12.0,
        "rainfall": 2.4,
        "condition": "Partly cloudy",
        "alert": "Weather is normal for planning.",
        "forecast": [
            {"time": "Today", "temperature": 29.5, "rainfall": 2.4, "summary": "Partly cloudy"},
            {"time": "Tomorrow", "temperature": 30.2, "rainfall": 5.0, "summary": "Light rain possible"},
        ],
        "source": "demo",
        "message": message,
        "error_reason": reason,
    }


def _weather_alert(rainfall: float) -> str:
    if rainfall > 20:
        return "Heavy rain risk. Check drainage before irrigation."
    return "Weather is normal for planning."


def _clean_error(status_code: int | None, response_text: str = "") -> tuple[str, str]:
    if status_code == 401:
        return "api_key_invalid", "OpenWeather API key is invalid. Demo weather data is shown."
    if status_code == 404:
        return "district_not_found", "District was not found by OpenWeather. Demo weather data is shown."
    if status_code:
        return "openweather_error", f"OpenWeather returned status {status_code}. Demo weather data is shown."
    return "network_error", "OpenWeather network error. Demo weather data is shown."


async def fetch_weather(district: str) -> dict:
    settings = get_settings()
    api_key = settings.openweather_api_key.strip()
    api_key_configured = bool(api_key and api_key != "your_api_key_here")
    sanitized_params = {"q": f"{district},IN", "units": "metric"}
    sanitized_url = f"{settings.openweather_base_url}/weather?{urlencode(sanitized_params)}"

    logger.info("OpenWeatherMap API key configured: %s", "yes" if api_key_configured else "no")
    logger.info("Requested district: %s", district)
    logger.info("OpenWeather URL without API key: %s", sanitized_url)

    if not api_key_configured:
        return _demo_weather(district, "API key missing. Demo weather data is shown.", "api_key_missing")

    params = {"q": f"{district},IN", "appid": api_key, "units": "metric"}
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            current_response = await client.get(f"{settings.openweather_base_url}/weather", params=params)
            logger.info("Weather API response status: %s", current_response.status_code)
            current_response.raise_for_status()
            forecast_response = await client.get(f"{settings.openweather_base_url}/forecast", params=params)
            logger.info("Weather forecast API response status: %s", forecast_response.status_code)
            forecast_response.raise_for_status()

        current_json = current_response.json()
        forecast_json = forecast_response.json()
        rainfall = float(current_json.get("rain", {}).get("1h", 0))
        condition = current_json["weather"][0]["description"]
        return {
            "district": district,
            "temperature": float(current_json["main"]["temp"]),
            "humidity": int(current_json["main"]["humidity"]),
            "wind": float(current_json["wind"].get("speed", 0)),
            "rainfall": rainfall,
            "condition": condition,
            "alert": _weather_alert(rainfall),
            "forecast": [
                {
                    "time": item["dt_txt"],
                    "temperature": float(item["main"]["temp"]),
                    "rainfall": float(item.get("rain", {}).get("3h", 0)),
                    "summary": item["weather"][0]["description"],
                }
                for item in forecast_json.get("list", [])[:8]
            ],
            "source": "openweathermap",
            "message": "Live weather updated.",
            "error_reason": None,
        }
    except httpx.TimeoutException:
        logger.info("Weather API response status: timeout")
        return _demo_weather(district, "OpenWeather request timed out. Demo weather data is shown.", "network_error")
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response else None
        logger.info("Weather API response status: %s", status_code)
        reason, message = _clean_error(status_code, exc.response.text if exc.response else "")
        return _demo_weather(district, message, reason)
    except httpx.HTTPError as exc:
        logger.info("Weather API response status: network_error")
        logger.warning("Weather network error for %s: %s", district, exc)
        return _demo_weather(district, "OpenWeather network error. Demo weather data is shown.", "network_error")
    except Exception as exc:
        logger.exception("Unexpected error fetching weather for %s", district)
        return _demo_weather(district, "OpenWeather error. Demo weather data is shown.", "openweather_error")
