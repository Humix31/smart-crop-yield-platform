import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tables import SensorCalibration, SensorData
from app.schemas.dto import SensorCalibrationIn, SensorCalibrationOut, SensorIn, SensorOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sensors", tags=["sensors"])


def _default_calibration(db: Session) -> SensorCalibration:
    calibration = db.query(SensorCalibration).order_by(SensorCalibration.id.asc()).first()
    if calibration:
        return calibration
    calibration = SensorCalibration(dry_value=3500, wet_value=1200, pump_on_below=35, pump_off_above=65)
    db.add(calibration)
    db.commit()
    db.refresh(calibration)
    return calibration


@router.post("", response_model=SensorOut)
def ingest_sensor(payload: SensorIn, db: Session = Depends(get_db)):
    """
    Ingest sensor data from ESP32 field hardware.
    """
    try:
        pump_status = payload.pump_status.upper().strip()
        esp32_status = payload.esp32_status.lower().strip()

        if not (0 <= payload.temperature <= 60):
            raise HTTPException(status_code=400, detail="Temperature out of range (0-60 C)")
        if not (0 <= payload.humidity <= 100):
            raise HTTPException(status_code=400, detail="Humidity must be 0-100%")
        if not (0 <= payload.soil_moisture <= 100):
            raise HTTPException(status_code=400, detail="Soil moisture must be 0-100%")
        if payload.soil_raw is not None and payload.soil_raw < 0:
            raise HTTPException(status_code=400, detail="soil_raw cannot be negative")
        if not (0 <= payload.soil_ph <= 14):
            raise HTTPException(status_code=400, detail="Soil pH must be 0-14")
        if payload.rainfall < 0:
            raise HTTPException(status_code=400, detail="Rainfall cannot be negative")
        if pump_status not in {"ON", "OFF"}:
            raise HTTPException(status_code=400, detail="pump_status must be ON or OFF")
        if esp32_status not in {"online", "offline"}:
            raise HTTPException(status_code=400, detail="esp32_status must be online or offline")

        row = SensorData(
            **payload.model_dump(exclude={"pump_status", "esp32_status"}),
            pump_status=pump_status,
            esp32_status=esp32_status,
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        logger.info("Sensor data recorded: pump %s, ESP32 %s", pump_status, esp32_status)
        return row

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error ingesting sensor data")
        raise HTTPException(status_code=500, detail=f"Failed to ingest sensor data: {str(e)}")


@router.get("/latest", response_model=SensorOut | None)
def latest_sensor(db: Session = Depends(get_db)):
    try:
        return db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
    except Exception:
        logger.exception("Error fetching latest sensor data")
        raise HTTPException(status_code=500, detail="Failed to fetch latest sensor data")


@router.get("/history", response_model=list[SensorOut])
def sensor_history(db: Session = Depends(get_db)):
    try:
        return db.query(SensorData).order_by(SensorData.timestamp.desc()).limit(50).all()
    except Exception:
        logger.exception("Error fetching sensor history")
        raise HTTPException(status_code=500, detail="Failed to fetch sensor history")


@router.get("/calibration", response_model=SensorCalibrationOut)
def get_calibration(db: Session = Depends(get_db)):
    try:
        return _default_calibration(db)
    except Exception:
        logger.exception("Error fetching sensor calibration")
        raise HTTPException(status_code=500, detail="Failed to fetch sensor calibration")


@router.post("/calibration", response_model=SensorCalibrationOut)
def save_calibration(payload: SensorCalibrationIn, db: Session = Depends(get_db)):
    try:
        if payload.dry_value == payload.wet_value:
            raise HTTPException(status_code=400, detail="Dry and wet calibration values must be different")
        if payload.pump_on_below >= payload.pump_off_above:
            raise HTTPException(status_code=400, detail="Pump ON threshold must be lower than Pump OFF threshold")

        calibration = _default_calibration(db)
        calibration.dry_value = payload.dry_value
        calibration.wet_value = payload.wet_value
        calibration.pump_on_below = payload.pump_on_below
        calibration.pump_off_above = payload.pump_off_above
        db.add(calibration)
        db.commit()
        db.refresh(calibration)
        return calibration
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        logger.exception("Error saving sensor calibration")
        raise HTTPException(status_code=500, detail="Failed to save sensor calibration")
