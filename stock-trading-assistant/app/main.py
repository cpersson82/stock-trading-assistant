"""
Stock Trading Assistant - Main Application
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager
import logging
import os

from app.database import init_db
from app.web.routes import router as web_router
from app.scheduler.jobs import run_scheduled_check
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting Stock Trading Assistant...")
    
    init_db()
    logger.info("Database initialized")
    
    # European market open (8:00 CET)
    scheduler.add_job(
        run_scheduled_check,
        CronTrigger(hour=8, minute=0, timezone='Europe/Zurich'),
        id='european_open',
        name='European Market Open Check',
        replace_existing=True
    )
    
    # US market open (15:30 CET)
    scheduler.add_job(
        run_scheduled_check,
        CronTrigger(hour=15, minute=30, timezone='Europe/Zurich'),
        id='us_open',
        name='US Market Open Check',
        replace_existing=True
    )
    
    # US market close (22:00 CET)
    scheduler.add_job(
        run_scheduled_check,
        CronTrigger(hour=22, minute=0, timezone='Europe/Zurich'),
        id='us_close',
        name='US Market Close Check',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Scheduler started with 3 daily market checks")
    
    yield
    
    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Stock Trading Assistant",
    description="AI-powered stock trading recommendation system",
    version="1.0.0",
    lifespan=lifespan
)

static_dir = "app/static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(web_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
