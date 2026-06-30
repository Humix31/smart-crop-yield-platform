import logging
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import time

from app.api import auth, predictions, sensors, weather
from app.core.config import get_settings
from sqlalchemy import inspect, text
from app.db.session import Base, engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)


settings = get_settings()
Base.metadata.create_all(bind=engine)



def ensure_sqlite_columns():
    if engine.dialect.name != "sqlite":
        return
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as connection:
        if "users" in table_names:
            existing_columns = {column["name"] for column in inspector.get_columns("users")}
            user_columns = {
                "name": "VARCHAR(120) DEFAULT ''",
                "phone": "VARCHAR(30)",
                "email": "VARCHAR(255) DEFAULT ''",
                "district": "VARCHAR(120)",
                "taluk": "VARCHAR(120)",
                "language": "VARCHAR(20) DEFAULT 'en'",
                "role": "VARCHAR(30) DEFAULT 'farmer'",
                "hashed_password": "VARCHAR(255) DEFAULT ''",
                "created_at": "DATETIME",
            }
            for column_name, column_definition in user_columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_definition}"))
                    logger.info("Added missing users.%s column", column_name)
            users_schema = connection.execute(text("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'")).scalar() or ""
            if "UNIQUE (phone)" in users_schema:
                logger.info("Removing obsolete unique constraint from users.phone")
                connection.execute(text("PRAGMA foreign_keys=off"))
                connection.execute(text("""
                    CREATE TABLE users_without_phone_unique (
                        id INTEGER NOT NULL PRIMARY KEY,
                        name VARCHAR(120) NOT NULL,
                        phone VARCHAR(30),
                        email VARCHAR(255) NOT NULL,
                        language VARCHAR(20) DEFAULT 'en',
                        role VARCHAR(30) DEFAULT 'farmer',
                        hashed_password VARCHAR(255) NOT NULL,
                        created_at DATETIME
                    )
                """))
                connection.execute(text("""
                    INSERT INTO users_without_phone_unique
                    (id, name, phone, email, language, role, hashed_password, created_at)
                    SELECT id, name, phone, email, language, role, hashed_password, created_at
                    FROM users
                """))
                connection.execute(text("DROP TABLE users"))
                connection.execute(text("ALTER TABLE users_without_phone_unique RENAME TO users"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)"))
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_created_at ON users (created_at)"))
                connection.execute(text("PRAGMA foreign_keys=on"))

        if "predictions" in table_names:
            existing_columns = {column["name"] for column in inspector.get_columns("predictions")}
            if "user_email" not in existing_columns:
                connection.execute(text("ALTER TABLE predictions ADD COLUMN user_email VARCHAR(255)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_predictions_user_email ON predictions (user_email)"))
                logger.info("Added missing predictions.user_email column")
            if "taluk" not in existing_columns:
                connection.execute(text("ALTER TABLE predictions ADD COLUMN taluk VARCHAR(120)"))
                logger.info("Added missing predictions.taluk column")
            if "village" not in existing_columns:
                connection.execute(text("ALTER TABLE predictions ADD COLUMN village VARCHAR(160)"))
                logger.info("Added missing predictions.village column")

        if "sensor_data" in table_names:
            existing_columns = {column["name"] for column in inspector.get_columns("sensor_data")}
            sensor_columns = {
                "soil_ph": "FLOAT DEFAULT 0",
                "rainfall": "FLOAT DEFAULT 0",
                "soil_raw": "FLOAT",
                "pump_status": "VARCHAR(20) DEFAULT 'OFF'",
                "esp32_status": "VARCHAR(30) DEFAULT 'offline'",
            }
            for column_name, column_definition in sensor_columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE sensor_data ADD COLUMN {column_name} {column_definition}"))
                    logger.info("Added missing sensor_data.%s column", column_name)

        if "sensor_calibration" in table_names:
            existing_columns = {column["name"] for column in inspector.get_columns("sensor_calibration")}
            calibration_columns = {
                "dry_value": "FLOAT DEFAULT 3500",
                "wet_value": "FLOAT DEFAULT 1200",
                "pump_on_below": "FLOAT DEFAULT 35",
                "pump_off_above": "FLOAT DEFAULT 65",
                "updated_at": "DATETIME",
            }
            for column_name, column_definition in calibration_columns.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE sensor_calibration ADD COLUMN {column_name} {column_definition}"))
                    logger.info("Added missing sensor_calibration.%s column", column_name)
ensure_sqlite_columns()

app = FastAPI(title=settings.app_name, version="1.0.0")

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {process_time:.2f}s"
        )
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"{request.method} {request.url.path} - ERROR - {str(e)} - {process_time:.2f}s"
        )
        raise

# Exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

logger.info(f"Starting {settings.app_name} in {settings.environment} mode")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(sensors.router, prefix="/api")
app.include_router(weather.router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Smart Crop Yield API</title>
        <style>
          body {
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: linear-gradient(135deg, #ecfdf5, #f8fafc 46%, #e0f2fe);
            color: #0f172a;
          }
          main {
            width: min(720px, calc(100% - 32px));
            border: 1px solid rgba(15, 23, 42, .08);
            border-radius: 18px;
            padding: 32px;
            background: rgba(255, 255, 255, .78);
            box-shadow: 0 24px 80px rgba(15, 23, 42, .14);
            backdrop-filter: blur(18px);
          }
          h1 { margin: 0 0 10px; font-size: clamp(30px, 5vw, 48px); }
          p { line-height: 1.7; color: #475569; }
          .links { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 24px; }
          a {
            border-radius: 10px;
            padding: 10px 14px;
            background: #047857;
            color: white;
            text-decoration: none;
            font-weight: 700;
          }
          a.secondary { background: #0f172a; }
          code {
            display: block;
            margin-top: 18px;
            padding: 14px;
            border-radius: 10px;
            background: #0f172a;
            color: #d1fae5;
            overflow-x: auto;
          }
        </style>
      </head>
      <body>
        <main>
          <h1>Smart Crop Yield API is running</h1>
          <p>
            This address is the FastAPI backend. The production React dashboard is in the
            <strong>frontend</strong> folder and should run on <strong>http://localhost:5173</strong>
            after installing Node/npm dependencies.
          </p>
          <div class="links">
            <a href="/docs">Open API Docs</a>
            <a class="secondary" href="/api/health">Health Check</a>
          </div>
          <code>cd frontend<br />npm install<br />npm run dev</code>
        </main>
      </body>
    </html>
    """


@app.get("/api/health")
def health():
    return {"status": "ok", "service": settings.app_name}





