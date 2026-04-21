from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, products, bids, requests, notifications, ratings, wishlist

app = FastAPI(
    title="Nittany Auction API",
    description="Backend API for the Nittany Auction platform — CMPSC 431W",
    version="0.1.0",
)

#allow CORS for the frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#register all le routers
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(bids.router)
app.include_router(requests.router)
app.include_router(notifications.router)
app.include_router(ratings.router)
app.include_router(wishlist.router)

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}