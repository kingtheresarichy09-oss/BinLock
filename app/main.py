import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI


from app import models
from app.database import SessionLocal
from app.routers.subscriptions import process_subscription_reminders

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


def run_subscription_reminder_check():
    db = SessionLocal()

    try:
        results = process_subscription_reminders(db)

        if any(results.values()):
            logger.info(
                "Subscription reminder check completed: %s",
                results,
            )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


async def expiry_scheduler():

    while True:
        try:
            await asyncio.to_thread(run_subscription_reminder_check)

        except Exception:
            logger.exception(
                "Subscription expiry and reminder check failed."
            )

        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):

    scheduler_task = asyncio.create_task(expiry_scheduler())

    logger.info(
        "BinLock subscription expiry and reminder scheduler started."
    )

    try:
        yield

    finally:
        scheduler_task.cancel()

        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass

        logger.info(
            "BinLock subscription expiry and reminder scheduler stopped."
        )


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
