import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI


from app import models
from app.database import SessionLocal
from app.routers.subscriptions import process_expired_subscriptions

from app.routers.auth import router as auth_router
from app.routers.bins import router as bins_router
from app.routers.pickups import router as pickups_router
from app.routers import subscriptions
from app.routers import payments
from app.routers import bin_access
from app.routers import organisations
from app.routers.collections import router as collections_router
from app.routers.service_requests import router as service_requests_router
from app.routers.deliveries import router as deliveries_router
from app.routers.analytics import router as analytics_router


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_expiry_check():
    """Run subscription expiry processing with a fresh database session."""
    db = SessionLocal()

    try:
        expired_count = process_expired_subscriptions(db)

        if expired_count:
            logger.info(
                "Subscription expiry check completed. "
                "%s subscription(s) expired.",
                expired_count,
            )

    finally:
        db.close()


async def expiry_scheduler():
    """Check for expired subscriptions every 60 seconds."""

    while True:
        try:
            await asyncio.to_thread(run_expiry_check)

        except Exception:
            logger.exception("Subscription expiry check failed.")

        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop the subscription expiry scheduler."""

    scheduler_task = asyncio.create_task(expiry_scheduler())

    logger.info("BinLock subscription expiry scheduler started.")

    try:
        yield

    finally:
        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        logger.info("BinLock subscription expiry scheduler stopped.")


app = FastAPI(
    title="BinLock API",
    description="Backend API for BinLock waste management platform",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(auth_router)
app.include_router(bins_router)
app.include_router(pickups_router)
app.include_router(subscriptions.router)
app.include_router(payments.router)
app.include_router(bin_access.router)
app.include_router(organisations.router)
app.include_router(collections_router)
app.include_router(service_requests_router)
app.include_router(deliveries_router)
app.include_router(analytics_router)


@app.get("/")
def home():
    return {
        "message": "Welcome to BinLock API",
        "status": "running",
    }
