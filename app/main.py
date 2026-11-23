from fastapi import FastAPI

from app.database import engine, Base
from app import models
from app.routers.auth import router as auth_router
from app.routers.bins import router as bins_router


app = FastAPI(
    title="BinLock API",
    description="Backend API for BinLock waste management platform",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(bins_router)

Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {
        "message": "Welcome to BinLock API",
        "status": "running"
    }