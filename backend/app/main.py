from fastapi import FastAPI, Depends
#from app.database import get_db


"""
This is the entrypoint file for FastAPI
Run it using a python virtual environment, starting the venv first and using:
    source venv/bin/activate
    uvicorn app.main:app --reload
to start the app

FastAPI automatically generates API Docs (Swagger spec) at:
    http://127.0.0.1:8000/redoc
"""

app = FastAPI(
    title="Nittany Auction API",
    description="Backend API for the Nittany Auction platform — CMPSC 431W",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {"message": "Hello World"}

"""
    Health check endpoint. Verifies the API is running and the
    database connection is working.
"""

"""
@app.get("/health")
def health_check(db=Depends(get_db)):

    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
"""