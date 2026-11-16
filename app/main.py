from fastapi import FastAPI 

app = FastAPI(
    title="BinLock API",
    description="Backend API FOR BinLock waste management platform",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "Welcome to BinLock API",
        "status": "running"
    }