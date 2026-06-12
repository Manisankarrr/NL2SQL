import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.config import settings
from backend.database.connection import create_pool, close_pool
from backend.database.schema_loader import get_schema
from backend.routers.query import router
from backend.middleware.logger import setup_logging, RequestLoggingMiddleware, pipeline_logger
from backend.middleware.error_handler import register_handlers
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("barbersql")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting BarberSQL...")
    await create_pool()
    await get_schema()
    logger.info("Database connected. Schema loaded. Ready.")

    # Auto-complete any past appointments missed while server was off
    try:
        from backend.database.executor import execute_sql
        result = await execute_sql(
            "UPDATE appointments SET status = 'completed' "
            "WHERE id > 0 AND ("
            "    appointment_date < CURDATE() OR ("
            "        appointment_date = CURDATE() AND "
            "        appointment_time < CURTIME()"
            "    )"
            ") AND status = 'scheduled';"
        )
        if result.success and result.affected_rows > 0:
            pipeline_logger.ok(
                f"Auto-completed {result.affected_rows} past appointment(s) on startup"
            )
    except Exception as e:
        logger.warning(f"Startup auto-complete failed: {e}")

    yield
    # Shutdown
    logger.info("Shutting down BarberSQL...")
    await close_pool()

app = FastAPI(
    title="BarberSQL",
    description="Natural Language to SQL assistant for Barber Shop booking",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(RequestLoggingMiddleware)
register_handlers(app)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include Router
app.include_router(router)


@app.get("/")
async def root():
    return {
        "status": "running",
        "app": "BarberSQL",
        "version": "1.0.0",
        "docs": "/docs",
        "frontend": "http://localhost:7860"
    }


if __name__ == "__main__":
    reload = settings.app_env == "development"
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=reload)

