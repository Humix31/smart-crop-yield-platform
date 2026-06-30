<<<<<<< HEAD
﻿# Smart Crop Yield Prediction Platform

A production-oriented full-stack platform for farmers and agriculture officers. It includes a React dashboard, FastAPI backend, SQLite/PostgreSQL persistence, JWT authentication, OpenWeatherMap integration, ESP32 sensor ingestion, multilingual UI, Tamil voice input, charts, map view, recommendations, and automatic loading of the existing Random Forest `.pkl` model files.

## Project Structure

```text
smart-crop-yield-platform/
  backend/
    app/
      api/                 FastAPI routes
      core/                config and security
      db/                  SQLAlchemy session
      models/              database tables
      schemas/             Pydantic DTOs
      services/            AI prediction and weather integrations
    models/                place crop_model.pkl and encoders here
    requirements.txt
    .env.example
  frontend/
    src/
      i18n/locales/        English, Tamil, Hindi, Malayalam, Telugu, Kannada
      services/api.js
      App.jsx
    package.json
    .env.example
  DEPLOYMENT.md
  render.yaml
```

## AI Model Files

Copy these files into `backend/models/`:

```text
crop_model.pkl
district_encoder.pkl
crop_encoder.pkl
season_encoder.pkl
```

The backend loads them automatically with Joblib at startup. If the files are missing, the API still runs with a deterministic demo estimator so the UI can be tested.

## Run Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

## Run Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend: `http://localhost:5173`

## ESP32 Sensor API

Send readings every few seconds. `soil_raw` is the direct ADC value from the ESP32 soil moisture sensor; `soil_moisture` can still be sent for compatibility, but the dashboard can calculate calibrated moisture from `soil_raw`.

```http
POST /api/sensors
Content-Type: application/json

{
  "temperature": 31.5,
  "humidity": 68,
  "soil_raw": 2850,
  "soil_moisture": 41,
  "soil_ph": 0,
  "rainfall": 0,
  "pump_status": "ON",
  "esp32_status": "online"
}
```

Calibration is available through the backend and dashboard:

```http
GET /api/sensors/calibration
POST /api/sensors/calibration
```

Use the calibration panel like this:

1. Put the probe in dry soil or open air and click **Set current as dry**.
2. Put the probe in wet soil or water and click **Set current as wet**.
3. Set pump thresholds, then save calibration.

The moisture formula is:

```text
moisture_percent = ((dry_value - soil_raw) / (dry_value - wet_value)) * 100
```

Clamp the final value between 0 and 100 in ESP32 firmware if you calculate it on-device. The backend stores raw readings, calibrated thresholds, `pump_status`, and `esp32_status` without breaking the existing sensor dashboard.

## Key Environment Variables

Backend:

```text
DATABASE_URL=sqlite:///./smart_crop.db
JWT_SECRET_KEY=change-this-before-production
OPENWEATHER_API_KEY=your_api_key_here
MODEL_DIR=./models
CORS_ORIGINS=http://localhost:5173
```

Frontend:

```text
VITE_API_BASE_URL=http://localhost:8000/api
VITE_GOOGLE_MAPS_EMBED_KEY=
```

## Production Notes

- Use PostgreSQL in production: `DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DB`.
- Replace `JWT_SECRET_KEY` with a strong secret.
- Configure CORS to the deployed frontend domain only.
- Mount or upload the four `.pkl` files to `backend/models/`.
- Add real Google OAuth verification before enabling public Google login. The current endpoint is a backend placeholder for frontend integration.


## Weather API Setup

The backend loads the OpenWeatherMap key from `backend/.env`. Do not put the API key in frontend code.

1. Open `backend/.env` or copy `backend/.env.example` to `.env`.
2. Set:

```text
OPENWEATHER_API_KEY=your_api_key_here
```

3. Restart the FastAPI backend.
4. Test:

```bash
curl http://127.0.0.1:8000/api/weather/Tiruchirappalli
```

If `OPENWEATHER_API_KEY` is empty or the API call fails, the backend returns demo weather with this message: `Live weather API key is not configured. Demo weather data is shown.`

## Official Tamil Nadu Location Dataset Required

The app intentionally does not ship fake taluk/village data. To enable the District -> Taluk -> Village dropdowns, provide an official government CSV/JSON from one of these sources:

- Tamil Nadu Government district/taluk/village dataset
- Local Government Directory (LGD) official CSV/JSON
- Government gazette administrative division dataset
- Census/government village directory

Required normalized JSON shape:

```json
{
  "Madurai": {
    "Madurai North": ["Official Village 1", "Official Village 2"],
    "Madurai South": ["Official Village 3"]
  }
}
```

Run the importer after downloading an official CSV/JSON:

```bash
python backend/scripts/import_tn_villages.py official_villages.csv --output frontend/src/data/tamilNaduLocations.json
```

The importer refuses files with no village rows, does not generate fake villages, and writes the normalized data to `frontend/src/data/tamilNaduLocations.json`.

## ESP32 Connection From Hardware

The ESP32 must post to your laptop IP address on the same Wi-Fi network. Do not use `127.0.0.1` in ESP32 code because that points back to the ESP32 itself.

Find your laptop IP on Windows:

```powershell
ipconfig
```

Look for the Wi-Fi adapter `IPv4 Address`, for example `192.168.x.x`. Use that address in the ESP32 HTTP URL:

```text
http://192.168.x.x:8000/api/sensors
```

Run the backend so other devices on the network can reach it:

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Run the frontend locally:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Windows Firewall may ask to allow Python/Uvicorn. Allow it on your private network so ESP32 requests can reach the backend.


=======
# Ai-powered-crop-yield-prediction-and-smart-farming-advisory
AI Powered Crop Yield Prediction and Smart Farming Advisory helps farmers predict crop yield using crop, season, area, rainfall, weather, and soil data. It also gives useful advice on irrigation, fertilizer, pest control, and crop management to improve productivity and reduce farming risks.
>>>>>>> 7e373f1b8ef099aa0d0b621eb940ce030cbb5d75
