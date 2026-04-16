from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, products

app = FastAPI(
    title="Nittany Auction API",
    description="Backend API for the Nittany Auction platform — CMPSC 431W",
    version="0.1.0",
)

# Allow CORS for the frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the auth routes (/api/login, /api/register, etc.)
app.include_router(auth.router)
app.include_router(products.router)

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}