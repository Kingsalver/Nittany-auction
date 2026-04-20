import os
import hashlib
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import pymysql

from app.database import get_db

# JWT config
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 120

# This tells FastAPI to look for a Bearer token in the Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)


def hash_password(password):
    """Hash a password using SHA-256 (same as setup_db.py)."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password, hashed_password):
    """Check if a plain password matches the stored hash."""
    return hash_password(plain_password) == hashed_password


def create_access_token(data, expires_delta=None):
    """Create a JWT token with user info inside it."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def get_user_role(email, cursor):
    """Figure out the user's role by checking the professor's tables."""
    cursor.execute("SELECT email FROM HelpDesk WHERE email = %s", (email,))
    if cursor.fetchone():
        return "HelpDesk"

    cursor.execute("SELECT email FROM Seller WHERE email = %s", (email,))
    if cursor.fetchone():
        return "Seller"

    cursor.execute("SELECT email FROM Bidder WHERE email = %s", (email,))
    if cursor.fetchone():
        return "Buyer"

    return "Buyer"


def get_current_user(token=Depends(oauth2_scheme), db=Depends(get_db)):
    """
    FastAPI dependency — extracts the user from the JWT token.
    Use this in any route that needs authentication:
        @router.get("/protected")
        def protected_route(user=Depends(get_current_user)):
            ...
    """
    if token is None:
        raise HTTPException(status_code=401, detail="Not logged in")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    with db.cursor() as cursor:
        # Make sure the session is still active
        cursor.execute(
            "SELECT session_id FROM Sessions WHERE token = %s AND is_active = 1 AND expires_at > NOW()",
            (token,)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=401, detail="Session expired or logged out")

        # Get the user from the database
        cursor.execute("SELECT email FROM User WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        role = payload.get("role", get_user_role(email, cursor))

    return {"email": email, "role": role}
