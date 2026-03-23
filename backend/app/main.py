from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.database import get_db
from pydantic import BaseModel
import hashlib

app = FastAPI(
    title="Nittany Auction API",
    description="Backend API for the Nittany Auction platform — CMPSC 431W",
    version="0.1.0",
)

# Allow CORS since Vite runs on port 5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/api/login")
def login(req: LoginRequest, db=Depends(get_db)):
    hashed = hashlib.sha256(req.password.encode()).hexdigest()
    with db.cursor() as cursor:
        cursor.execute("SELECT email FROM User WHERE email = %s AND password = %s", (req.email, hashed))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials. Please try again.")
            
        # Check Roles
        cursor.execute("SELECT email FROM Seller WHERE email = %s", (req.email,))
        if cursor.fetchone():
            return {"user": {"email": req.email, "role": "Seller"}}
            
        cursor.execute("SELECT email FROM HelpDesk WHERE email = %s", (req.email,))
        if cursor.fetchone():
            return {"user": {"email": req.email, "role": "HelpDesk"}}
            
        cursor.execute("SELECT email FROM Bidder WHERE email = %s", (req.email,))
        if cursor.fetchone():
            return {"user": {"email": req.email, "role": "Buyer"}}
            
        return {"user": {"email": req.email, "role": "Buyer"}}

@app.get("/api/health")
def health_check(db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}