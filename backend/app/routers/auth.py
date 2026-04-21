from datetime import timedelta, datetime, timezone
import pymysql

from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.schemas import LoginRequest, RegisterRequest, Token, ProfileUpdate, PasswordUpdate
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
    #Auth for user login. This function returns a JWT token for the auth
    with db.cursor() as cursor:
        #first we have to check if the user exists
        cursor.execute("SELECT email, password FROM User WHERE email = %s", (req.email,))
        user = cursor.fetchone()

        #if we cant find the user we raise an except.
        if not user or not verify_password(req.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        #get the users role
        role = get_user_role(req.email, cursor)

    #create a JWT token with the user's email and role for auth
    expires = timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": req.email, "role": role},
        expires_delta=expires,
    )

    #save the token and the session in the Sessions table
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
def register(req: RegisterRequest, db=Depends(get_db)):
    #route to register a new user as a Buyer. We also insert into User, Address (if address given), and Bidder
    import uuid

    with db.cursor() as cursor:
        #quick check if email is already taken
        cursor.execute("SELECT email FROM User WHERE email = %s", (req.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        #insert into User table with hashed password
        hashed = hash_password(req.password)
        name = f"{req.first_name} {req.last_name}"
        cursor.execute(
            "INSERT INTO User (email, password, name) VALUES (%s, %s, %s)",
            (req.email, hashed, name),
        )

        #this is to handle the optional address and zipcode. we create the row if its new.
        home_address_id = None
        if req.zipcode:
            #check the zip exists in ZipCode table (seeded from dataset)
            cursor.execute("SELECT zipcode FROM ZipCode WHERE zipcode = %s", (req.zipcode,))
            if cursor.fetchone():
                #generate a new UUID for this address
                home_address_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO Address (address_id, zipcode, street_num, street_name) VALUES (%s, %s, %s, %s)",
                    (home_address_id, req.zipcode, req.street_num, req.street_name),
                )
            #if zipcode doesn't exist in our table, skip address

        #insert into Bidder table with all optional fields
        cursor.execute(
            "INSERT INTO Bidder (email, first_name, last_name, age, major, home_address_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (req.email, req.first_name, req.last_name, req.age, req.major, home_address_id),
        )
    db.commit()

    #when they create the account and its successful we can just create a token right away and log them in
    #realistically should create a function for this code block but eh
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
    #get the currently logged in user's info but they need a valid token
    return current_user


@router.get("/profile")
def get_profile(current_user=Depends(get_current_user), db=Depends(get_db)):
    #get the full profile of the logged in user User + Bidder + Address joined
    email = current_user["email"]

    with db.cursor() as cursor:
        #get base user info
        cursor.execute("SELECT email, name FROM User WHERE email = %s", (email,))
        user = cursor.fetchone()

        #get bidder info if they are a bidder
        cursor.execute(
            """
            SELECT b.first_name, b.last_name, b.age, b.major, b.phone, b.annual_income,
                   a.street_num, a.street_name, a.zipcode,
                   z.city, z.state
            FROM Bidder b
            LEFT JOIN Address a ON b.home_address_id = a.address_id
            LEFT JOIN ZipCode z ON a.zipcode = z.zipcode
            WHERE b.email = %s
            """,
            (email,)
        )
        bidder = cursor.fetchone()

    return {
        "email": user["email"],
        "name": user["name"],
        "role": current_user["role"],
        "first_name": bidder["first_name"] if bidder else None,
        "last_name": bidder["last_name"] if bidder else None,
        "age": bidder["age"] if bidder else None,
        "major": bidder["major"] if bidder else None,
        "phone": bidder["phone"] if bidder else None,
        "street_num": bidder["street_num"] if bidder else None,
        "street_name": bidder["street_name"] if bidder else None,
        "zipcode": bidder["zipcode"] if bidder else None,
        "city": bidder["city"] if bidder else None,
        "state": bidder["state"] if bidder else None,
    }


@router.patch("/profile")
def update_profile(req: ProfileUpdate, current_user=Depends(get_current_user), db=Depends(get_db)):
    #this is for the update feature on the profile page, we let them update the bidder phone number and home address
    import uuid
    email = current_user["email"]

    with db.cursor() as cursor:
        #update phone directly on Bidder
        if req.phone is not None:
            cursor.execute(
                "UPDATE Bidder SET phone = %s WHERE email = %s",
                (req.phone, email)
            )

        #handle address update
        if req.zipcode is not None:
            # Check zip exists
            cursor.execute("SELECT zipcode FROM ZipCode WHERE zipcode = %s", (req.zipcode,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"ZIP code '{req.zipcode}' not found")

            #check if bidder already has an address
            cursor.execute(
                "SELECT home_address_id FROM Bidder WHERE email = %s", (email,)
            )
            row = cursor.fetchone()
            existing_id = row["home_address_id"] if row else None

            if existing_id:
                #update the existing Address row
                cursor.execute(
                    "UPDATE Address SET zipcode=%s, street_num=%s, street_name=%s WHERE address_id=%s",
                    (req.zipcode, req.street_num, req.street_name, existing_id)
                )
            else:
                #create a new Address row and link it
                new_id = str(uuid.uuid4())
                cursor.execute(
                    "INSERT INTO Address (address_id, zipcode, street_num, street_name) VALUES (%s,%s,%s,%s)",
                    (new_id, req.zipcode, req.street_num, req.street_name)
                )
                cursor.execute(
                    "UPDATE Bidder SET home_address_id = %s WHERE email = %s",
                    (new_id, email)
                )
    db.commit()
    return {"detail": "Profile updated successfully"}


@router.patch("/profile/password")
def change_password(req: PasswordUpdate, current_user=Depends(get_current_user), db=Depends(get_db)):
    email = current_user["email"]
    with db.cursor() as cursor:
        cursor.execute("SELECT password FROM User WHERE email = %s", (email,))
        user = cursor.fetchone()
        if not user or not verify_password(req.current_password, user["password"]):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        cursor.execute(
            "UPDATE User SET password = %s WHERE email = %s",
            (hash_password(req.new_password), email),
        )
    db.commit()
    return {"detail": "Password updated successfully"}


@router.post("/logout")
def logout(current_user=Depends(get_current_user), db=Depends(get_db)):
    #route to log users out, we just deactivate all the sessions on the user
    with db.cursor() as cursor:
        cursor.execute(
            "UPDATE Sessions SET is_active = 0 WHERE user_email = %s AND is_active = 1",
            (current_user["email"],),
        )
    db.commit()
    return {"detail": "Logged out successfully"}
