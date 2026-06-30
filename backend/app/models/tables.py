from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    taluk: Mapped[str | None] = mapped_column(String(120), nullable=True)
    language: Mapped[str] = mapped_column(String(20), default="en")
    role: Mapped[str] = mapped_column(String(30), default="farmer", index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    district: Mapped[str] = mapped_column(String(120), index=True)
    taluk: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    village: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    crop: Mapped[str] = mapped_column(String(120), index=True)
    season: Mapped[str] = mapped_column(String(80), index=True)
    area: Mapped[float] = mapped_column(Float)
    rainfall: Mapped[float] = mapped_column(Float)
    normal_rainfall: Mapped[float] = mapped_column(Float, default=0)
    deviation: Mapped[float] = mapped_column(Float, default=0)
    prediction: Mapped[float] = mapped_column(Float)
    recommendation: Mapped[str] = mapped_column(Text)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_district_crop_date", "district", "crop", "date"),
        Index("idx_date_desc", "date"),
    )


class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    temperature: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)
    soil_moisture: Mapped[float] = mapped_column(Float)
    soil_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_ph: Mapped[float] = mapped_column(Float)
    rainfall: Mapped[float] = mapped_column(Float)
    pump_status: Mapped[str] = mapped_column(String(20), default="OFF")
    esp32_status: Mapped[str] = mapped_column(String(30), default="online")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_timestamp_desc", "timestamp"),
    )


class SensorCalibration(Base):
    __tablename__ = "sensor_calibration"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dry_value: Mapped[float] = mapped_column(Float, default=3500)
    wet_value: Mapped[float] = mapped_column(Float, default=1200)
    pump_on_below: Mapped[float] = mapped_column(Float, default=35)
    pump_off_above: Mapped[float] = mapped_column(Float, default=65)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)


class Weather(Base):
    __tablename__ = "weather"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    district: Mapped[str] = mapped_column(String(120), index=True)
    temperature: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)
    wind: Mapped[float] = mapped_column(Float)
    rainfall: Mapped[float] = mapped_column(Float)
    forecast: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_district_fetched", "district", "fetched_at"),
    )
