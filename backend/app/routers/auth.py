from datetime import timedelta, datetime, timezone
import pymysql

from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.schemas import LoginRequest, Token
from app.auth import (
    TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
    get_user_role,
)

router = APIRouter(prefix="/api", tags=["Authentication"])


@router.post("/login")
def login(req: LoginRequest, db=Depends(get_db)):
    """Log in with email and password. Returns a JWT token."""
    with db.cursor() as cursor:
        # Check if the user exists
        cursor.execute("SELECT email, password FROM User WHERE email = %s", (req.email,))
        user = cursor.fetchone()

        if not user or not verify_password(req.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Figure out the user's role
        role = get_user_role(req.email, cursor)

    # Create a JWT token with the user's email and role
    expires = timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": req.email, "role": role},
        expires_delta=expires,
    )

    # Save the session in the Sessions table
    expires_at = datetime.now(timezone.utc) + expires
    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO Sessions (user_email, token, expires_at) VALUES (%s, %s, %s)",
            (req.email, access_token, expires_at.strftime("%Y-%m-%d %H:%M:%S")),
        )
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": role,
        "email": req.email,
    }


@router.post("/register")
def register(req: LoginRequest, db=Depends(get_db)):
    """Register a new user. Hashes the password and stores it."""
    with db.cursor() as cursor:
        # Check if email is already taken
        cursor.execute("SELECT email FROM User WHERE email = %s", (req.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Insert the new user with hashed password
        hashed = hash_password(req.password)
        cursor.execute(
            "INSERT INTO User (email, password) VALUES (%s, %s)",
            (req.email, hashed),
        )
    db.commit()

    # Auto-login: create a token right away
    expires = timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": req.email, "role": "Buyer"},
        expires_delta=expires,
    )

    expires_at = datetime.now(timezone.utc) + expires
    with db.cursor() as cursor:
        cursor.execute(
            "INSERT INTO Sessions (user_email, token, expires_at) VALUES (%s, %s, %s)",
            (req.email, access_token, expires_at.strftime("%Y-%m-%d %H:%M:%S")),
        )
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": "Buyer",
        "email": req.email,
    }


@router.get("/users/me")
def get_me(current_user=Depends(get_current_user)):
    """Get the currently logged-in user's info. Requires a valid token."""
    return current_user


@router.post("/logout")
def logout(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Log out by deactivating all sessions for this user."""
    with db.cursor() as cursor:
        cursor.execute(
            "UPDATE Sessions SET is_active = 0 WHERE user_email = %s AND is_active = 1",
            (current_user["email"],),
        )
    db.commit()
    return {"detail": "Logged out successfully"}
