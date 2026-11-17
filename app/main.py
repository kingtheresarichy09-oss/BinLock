from fastapi import FastAPI

from app.database import engine, Base
from app import models

app = FastAPI(
    title="BinLock API",
    description="Backend API FOR BinLock waste management platform",
    version="1.0.0"
)

Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {
        "message": "Welcome to BinLock API",
        "status": "running"
    }