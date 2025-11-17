from fastapi import FastAPI

app = FastAPI(title="NYC Transit Analytics API")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "nyc-transit-analytics"}


