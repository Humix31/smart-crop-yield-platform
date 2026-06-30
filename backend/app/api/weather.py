import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tables import Weather
from app.schemas.dto import WeatherOut
from app.core.config import get_settings
from app.services.weather_service import fetch_weather

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/{district}", response_model=WeatherOut)
async def district_weather(district: str, db: Session = Depends(get_db)):
    """
    Get current weather and forecast for a district.
    
    Returns demo data if API is unavailable.
    """
    district_name = district.strip()

    if not district_name:
        raise HTTPException(status_code=400, detail="District name cannot be empty")

    if len(district_name) > 120:
        raise HTTPException(status_code=400, detail="District name too long")

    try:
        logger.info(f"Fetching weather for district: {district_name}")
        data = await fetch_weather(district_name)

        weather_record = Weather(
            district=district_name,
            temperature=data["temperature"],
            humidity=data["humidity"],
            wind=data["wind"],
            rainfall=data["rainfall"],
            forecast=json.dumps(data["forecast"]),
        )
        db.add(weather_record)
        db.commit()
        
        logger.info(f"Weather fetched successfully for {district_name}")
        return data

    except Exception as e:
        db.rollback()
        logger.exception(f"Error fetching weather for {district_name}")
        fallback_data = {
            "district": district_name,
            "temperature": 29.5,
            "humidity": 68,
            "wind": 12.0,
            "rainfall": 2.4,
            "forecast": [
                {"time": "Today", "temperature": 29.5, "rainfall": 2.4, "summary": "Partly cloudy"},
                {"time": "Tomorrow", "temperature": 30.2, "rainfall": 5.0, "summary": "Light rain possible"},
            ],
            "source": "demo",
        }
        return fallback_data



@router.get("/debug/{district}")
async def weather_debug(district: str):
    """Debug-safe weather check. Never returns or logs the API key."""
    settings = get_settings()
    district_name = district.strip()
    if not district_name:
        raise HTTPException(status_code=400, detail="District name cannot be empty")
    data = await fetch_weather(district_name)
    return {
        "api_key_configured": bool(settings.openweather_api_key.strip() and settings.openweather_api_key.strip() != "your_api_key_here"),
        "requested_district": district_name,
        "openweather_url_without_key": f"{settings.openweather_base_url}/weather?q={district_name},IN&units=metric",
        "source": data.get("source"),
        "message": data.get("message"),
        "error_reason": data.get("error_reason"),
    }
