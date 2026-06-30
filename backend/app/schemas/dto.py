from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = None
    district: str | None = None
    taluk: str | None = None
    email: EmailStr
    password: str = Field(min_length=6)
    language: str = "en"
    role: Literal["farmer", "admin", "officer"] = "farmer"


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    role: Literal["farmer", "admin", "officer"] | None = None


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    district: str | None = None
    taluk: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    id: int
    email: EmailStr
    role: str
    name: str
    district: str | None = None
    taluk: str | None = None


class PredictionRequest(BaseModel):
    district: str
    taluk: str | None = None
    village: str | None = None
    crop: str
    season: str
    area: float = Field(gt=0)
    actual_rainfall: float = Field(ge=0)
    normal_rainfall: float = Field(ge=0)
    deviation: float


class Recommendation(BaseModel):
    fertilizer: str
    irrigation: str
    sowing_period: str
    harvest_period: str
    alert: str


class PredictionResponse(BaseModel):
    predicted_yield: float
    unit: str = "tons/hectare"
    recommendation: Recommendation
    model_status: str
    location_note: str
    location: dict[str, str | None]


class SensorIn(BaseModel):
    temperature: float
    humidity: float
    soil_moisture: float
    soil_raw: float | None = None
    soil_ph: float
    rainfall: float
    pump_status: str = "OFF"
    esp32_status: str = "online"


class SensorOut(SensorIn):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class SensorCalibrationIn(BaseModel):
    dry_value: float = Field(ge=0)
    wet_value: float = Field(ge=0)
    pump_on_below: float = Field(ge=0, le=100)
    pump_off_above: float = Field(ge=0, le=100)


class SensorCalibrationOut(SensorCalibrationIn):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class WeatherOut(BaseModel):
    district: str
    temperature: float
    humidity: float
    wind: float
    rainfall: float
    condition: str | None = None
    alert: str | None = None
    forecast: list[dict]
    source: str | None = None
    message: str | None = None
    error_reason: str | None = None
