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

# grab bearer token from headers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login", auto_error=False)


def hash_password(password):
    # hash pass to match what we put in setup_db
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password, hashed_password):
    # check if password is right
    return hash_password(plain_password) == hashed_password


def create_access_token(data, expires_delta=None):
    # make a new token
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def get_user_role(email, cursor):
    # figure out user role by checking the tables
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
    # get the logged in user from the token for protected routes
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
        # check if session is still good
        cursor.execute(
            "SELECT session_id FROM Sessions WHERE token = %s AND is_active = 1 AND expires_at > NOW()",
            (token,)
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=401, detail="Session expired or logged out")

        # get user from db
        cursor.execute("SELECT email FROM User WHERE email = %s", (email,))
        user = cursor.fetchone()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")

        role = payload.get("role", get_user_role(email, cursor))

    return {"email": email, "role": role}
