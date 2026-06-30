from pathlib import Path
import logging

import joblib
import numpy as np

from app.core.config import get_settings
from app.schemas.dto import PredictionRequest, Recommendation

logger = logging.getLogger(__name__)

# Map all 38 Tamil Nadu districts to historical labels used by the trained model.
DISTRICT_MAPPING = {
    "Ariyalur": "ARIYALUR",
    "Chengalpattu": "KANCHIPURAM",
    "Chennai": "CHENNAI",
    "Coimbatore": "COIMBATORE",
    "Cuddalore": "CUDDALORE",
    "Dharmapuri": "DHARMAPURI",
    "Dindigul": "DINDIGUL",
    "Erode": "ERODE",
    "Kallakurichi": "VILLUPURAM",
    "Kancheepuram": "KANCHIPURAM",
    "Kanchipuram": "KANCHIPURAM",
    "Kanniyakumari": "KANNIYAKUMARI",
    "Karur": "KARUR",
    "Krishnagiri": "KRISHNAGIRI",
    "Madurai": "MADURAI",
    "Mayiladuthurai": "NAGAPATTINAM",
    "Nagapattinam": "NAGAPATTINAM",
    "Namakkal": "NAMAKKAL",
    "Nilgiris": "THE NILGIRIS",
    "The Nilgiris": "THE NILGIRIS",
    "Perambalur": "PERAMBALUR",
    "Pudukkottai": "PUDUKKOTTAI",
    "Ramanathapuram": "RAMANATHAPURAM",
    "Ranipet": "VELLORE",
    "Salem": "SALEM",
    "Sivaganga": "SIVAGANGA",
    "Tenkasi": "TIRUNELVELI",
    "Thanjavur": "THANJAVUR",
    "Theni": "THENI",
    "Thoothukudi": "TUTICORIN",
    "Thoothukkudi": "TUTICORIN",
    "Tiruchirappalli": "TIRUCHIRAPPALLI",
    "Trichy": "TIRUCHIRAPPALLI",
    "Tirunelveli": "TIRUNELVELI",
    "Tirupathur": "VELLORE",
    "Tiruppur": "TIRUPPUR",
    "Tiruvallur": "THIRUVALLUR",
    "Thiruvallur": "THIRUVALLUR",
    "Tiruvannamalai": "TIRUVANNAMALAI",
    "Tiruvarur": "THIRUVARUR",
    "Thiruvarur": "THIRUVARUR",
    "Vellore": "VELLORE",
    "Viluppuram": "VILLUPURAM",
    "Villupuram": "VILLUPURAM",
    "Virudhunagar": "VIRUDHUNAGAR",
}

class CropYieldPredictor:

    def __init__(self):
        settings = get_settings()

        self.model_dir = Path(settings.model_dir)

        self.model = None
        self.district_encoder = None
        self.crop_encoder = None
        self.season_encoder = None

        self.status = "demo-estimator"
        self._known_districts = set()

        self.load()

    def load(self):
        """Load trained models and encoders from disk."""
        try:
            logger.info(f"Loading models from {self.model_dir}...")

            self.model = joblib.load(
                self.model_dir / "crop_model.pkl"
            )
            logger.debug("Loaded crop_model.pkl")

            self.district_encoder = joblib.load(
                self.model_dir / "district_encoder.pkl"
            )
            logger.debug("Loaded district_encoder.pkl")

            self.crop_encoder = joblib.load(
                self.model_dir / "crop_encoder.pkl"
            )
            logger.debug("Loaded crop_encoder.pkl")

            self.season_encoder = joblib.load(
                self.model_dir / "season_encoder.pkl"
            )
            logger.debug("Loaded season_encoder.pkl")

            if hasattr(self.district_encoder, "classes_"):
                self._known_districts = {
                    str(value) for value in self.district_encoder.classes_
                }

            self.status = "loaded"
            logger.info("All models loaded successfully")

        except FileNotFoundError as e:
            self.status = f"missing-model-files: {str(e)}"
            logger.warning(f"Model files not found: {str(e)}")

        except Exception as e:
            self.status = f"model-load-error: {str(e)}"
            logger.error(f"Failed to load models: {str(e)}")

    def _encode(self, encoder, value):
        """
        Encode categorical values using fitted encoders.
        Returns 0 if encoding fails (unknown category).
        """
        if encoder is None:
            return 0

        try:
            encoded = int(encoder.transform([value])[0])
            return encoded

        except (ValueError, KeyError):
            logger.debug(f"Unknown category for encoder: {value}")
            return 0
        except Exception as e:
            logger.warning(f"Error encoding {value}: {str(e)}")
            return 0

    def _normalize_district(self, district: str) -> str:
        """Map districts to trained encoder labels when possible."""
        if not district:
            return district

        normalized = district.strip()
        mapped = DISTRICT_MAPPING.get(normalized, normalized)

        if not self._known_districts:
            return mapped

        for candidate in (mapped, normalized, normalized.title(), normalized.upper(), mapped.upper()):
            if candidate in self._known_districts:
                return candidate

        return mapped

    def predict(self, payload: PredictionRequest):
        """
        Predict crop yield based on input parameters.
        Uses trained model if available, falls back to demo estimator.
        """
        if self.model is not None:
            try:
                mapped_district = self._normalize_district(payload.district)

                features = np.array([[
                    self._encode(
                        self.district_encoder,
                        mapped_district
                    ),

                    2025,

                    self._encode(
                        self.season_encoder,
                        payload.season
                    ),

                    self._encode(
                        self.crop_encoder,
                        payload.crop
                    ),

                    payload.area,

                    payload.actual_rainfall,

                    payload.normal_rainfall,

                    payload.deviation
                ]])

                prediction = self.model.predict(features)
                result = round(float(prediction[0]), 2)
                
                logger.debug(
                    f"Prediction for {payload.district}/{payload.crop}: {result}"
                )
                return result

            except Exception as e:
                logger.error(f"Error during prediction: {str(e)}")
                # Fall through to demo estimator

        # Demo prediction if model not loaded
        logger.debug(f"Using demo estimator for prediction")
        
        rain_score = min(
            payload.actual_rainfall /
            max(payload.normal_rainfall, 1),
            1.45
        )

        crop_factor = (
            1 +
            (sum(ord(c) for c in payload.crop.lower()) % 17)
            / 100
        )

        season_factor = (
            1.08
            if payload.season.lower() in ["kharif", "summer"]
            else 0.96
        )

        estimate = (
            2.2 *
            rain_score *
            crop_factor *
            season_factor
        ) + (
            payload.area * 0.015
        )

        return round(max(0.25, estimate), 2)


def build_recommendation(
    payload: PredictionRequest,
    predicted_yield: float
):
    """
    Build personalized crop recommendations based on prediction and conditions.
    """
    logger.debug(f"Building recommendations for {payload.crop}")
    
    moisture_alert = (
        "Monitor soil moisture daily and irrigate if it falls below 35%."
    )

    # Determine irrigation advice based on rainfall deviation
    if payload.deviation < -20:
        irrigation = (
            "Use drip irrigation in two short cycles and mulch the field."
        )
        alert = (
            "Rainfall is below normal. Prioritize water conservation."
        )
    elif payload.deviation > 25:
        irrigation = (
            "Avoid over-irrigation and keep drainage channels open."
        )
        alert = (
            "Heavy rainfall risk. Watch for fungal disease."
        )
    else:
        irrigation = (
            "Maintain scheduled irrigation based on soil moisture."
        )
        alert = moisture_alert

    # Crop-specific recommendations
    crop = payload.crop.lower()

    if "rice" in crop or "paddy" in crop or "Ã Â®Â¨Ã Â¯â€ Ã Â®Â²Ã Â¯Â" in crop:
        fertilizer = (
            "Apply balanced NPK and split nitrogen doses."
        )
        sowing = (
            "June-July for Kharif or December-January under irrigation."
        )
        harvest = (
            "110-140 days after sowing."
        )
    elif "tomato" in crop or "Ã Â®Â¤Ã Â®â€¢Ã Â¯ÂÃ Â®â€¢Ã Â®Â¾Ã Â®Â³Ã Â®Â¿" in crop:
        fertilizer = (
            "Use compost and NPK 19:19:19 during early growth."
        )
        sowing = (
            "June-September or January-February."
        )
        harvest = (
            "70-90 days after transplanting."
        )
    elif "sugarcane" in crop or "Ã Â®â€¢Ã Â®Â°Ã Â¯ÂÃ Â®Â®Ã Â¯ÂÃ Â®ÂªÃ Â¯Â" in crop:
        fertilizer = (
            "Apply farmyard manure and split NPK doses over growing period."
        )
        sowing = (
            "October-November for better yields."
        )
        harvest = (
            "12 months after planting."
        )
    elif "maize" in crop or "Ã Â®Â®Ã Â®â€¢Ã Â¯ÂÃ Â®â€¢Ã Â®Â¾Ã Â®Å¡Ã Â¯ÂÃ Â®Å¡Ã Â¯â€¹Ã Â®Â³Ã Â®Â®Ã Â¯Â" in crop:
        fertilizer = (
            "Apply NPK 20:60:40 at planting and top-dress with nitrogen."
        )
        sowing = (
            "May-June for summer or September-October for winter."
        )
        harvest = (
            "100-120 days after sowing."
        )
    elif "groundnut" in crop or "Ã«â€¢â€¦Ã¬Â½Â©" in crop:
        fertilizer = (
            "Use balanced NPK with sufficient calcium."
        )
        sowing = (
            "June-July for Kharif or January for Rabi."
        )
        harvest = (
            "100-120 days after sowing."
        )
    else:
        fertilizer = (
            "Apply soil-test based NPK and farmyard manure."
        )
        sowing = (
            "Use the recommended sowing period for your locality."
        )
        harvest = (
            "Harvest at crop maturity."
        )

    # Adjust recommendations based on predicted yield
    if predicted_yield < 1.5:
        fertilizer += (
            " Add organic manure to improve soil fertility."
        )
    elif predicted_yield > 3.5:
        fertilizer += (
            " Maintain current practices and plan for market readiness."
        )

    return Recommendation(
        fertilizer=fertilizer,
        irrigation=irrigation,
        sowing_period=sowing,
        harvest_period=harvest,
        alert=alert
    )


predictor = CropYieldPredictor()



