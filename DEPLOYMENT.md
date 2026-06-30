# Deployment Guide

## Backend on Render

1. Create a new Render Web Service.
2. Set root directory to `backend`.
3. Use Python environment.
4. Build command:

```bash
pip install -r requirements.txt
```

5. Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

6. Add environment variables:

```text
ENVIRONMENT=production
DATABASE_URL=postgresql://...
JWT_SECRET_KEY=<strong-secret>
OPENWEATHER_API_KEY=<key>
MODEL_DIR=./models
CORS_ORIGINS=https://your-frontend-domain
```

7. Upload or mount the model files:

```text
backend/models/crop_model.pkl
backend/models/district_encoder.pkl
backend/models/crop_encoder.pkl
backend/models/season_encoder.pkl
```

## Frontend on Render

1. Create a Static Site.
2. Set root directory to `frontend`.
3. Build command:

```bash
npm install && npm run build
```

4. Publish directory:

```text
dist
```

5. Add:

```text
VITE_API_BASE_URL=https://your-backend-domain/api
```

## Railway Alternative

Backend:

```bash
railway init
railway add postgresql
railway variables set JWT_SECRET_KEY=<strong-secret>
railway variables set OPENWEATHER_API_KEY=<key>
railway up
```

Frontend:

```bash
railway init
railway variables set VITE_API_BASE_URL=https://your-backend-domain/api
railway up
```

## Health Checks

Backend:

```text
GET /api/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "Smart Crop Yield API"
}
```
