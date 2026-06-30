import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.tables import Prediction, User
from app.schemas.dto import PredictionRequest, PredictionResponse
from app.services.prediction_service import build_recommendation, predictor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["predictions"])
security = HTTPBearer()

LOCATION_NOTE = (
    "Prediction is generated using district-level historical crop and rainfall data. "
    "Taluk and village are used for better localization and farmer record keeping."
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired login. Please login again.")

    email = str(claims.get("sub") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=401, detail="Invalid login token. Please login again.")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User account not found. Please login again.")
    return user


@router.post("", response_model=PredictionResponse)
def create_prediction(
    payload: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a yield prediction based on input parameters.
    Stores prediction in database and returns result with recommendations.
    """
    print("Backend received prediction payload:", payload.model_dump())
    logger.info("Backend received prediction payload: %s", payload.model_dump())
    district = payload.district.strip()
    taluk = (payload.taluk or "").strip() or None
    village = (payload.village or "").strip() or None
    crop = payload.crop.strip()
    season = payload.season.strip()

    try:
        if not district or not crop or not season:
            raise HTTPException(status_code=400, detail="District, crop, and season are required")

        if payload.area <= 0:
            raise HTTPException(status_code=400, detail="Area must be greater than 0")

        if payload.area > 1000:
            raise HTTPException(status_code=400, detail="Area exceeds reasonable limit (1000 hectares)")

        if payload.actual_rainfall < 0 or payload.normal_rainfall < 0:
            raise HTTPException(status_code=400, detail="Rainfall values must be non-negative")

        logger.info(
            "Predicting yield for %s/%s/%s/%s (%s hectares)",
            district,
            taluk or "no-taluk",
            village or "no-village",
            crop,
            payload.area,
        )

        predicted = predictor.predict(payload)
        recommendation = build_recommendation(payload, predicted)

        record = Prediction(
            user_email=current_user.email,
            district=district,
            taluk=taluk,
            village=village,
            crop=crop,
            season=season,
            area=payload.area,
            rainfall=payload.actual_rainfall,
            normal_rainfall=payload.normal_rainfall,
            deviation=payload.deviation,
            prediction=predicted,
            recommendation=json.dumps(recommendation.model_dump()),
        )
        db.add(record)
        db.commit()

        logger.info("Prediction saved: %s/%s/%s/%s = %s tons/hectare", district, taluk or "no-taluk", village or "no-village", crop, predicted)

        return PredictionResponse(
            predicted_yield=predicted,
            recommendation=recommendation,
            model_status=predictor.status,
            location_note=LOCATION_NOTE,
            location={"district": district, "taluk": taluk, "village": village},
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Error creating prediction")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/history")
def history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get prediction history (last 25 predictions).
    """
    try:
        logger.info("Fetching prediction history for %s", current_user.email)
        rows = (
            db.query(Prediction)
            .filter(Prediction.user_email == current_user.email)
            .order_by(Prediction.date.desc())
            .limit(25)
            .all()
        )

        return [
            {
                "id": row.id,
                "district": row.district,
                "taluk": row.taluk,
                "village": row.village,
                "crop": row.crop,
                "season": row.season,
                "area": row.area,
                "rainfall": row.rainfall,
                "prediction": row.prediction,
                "date": row.date,
            }
            for row in rows
        ]

    except Exception as e:
        db.rollback()
        logger.exception("Error fetching prediction history")
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {str(e)}")

