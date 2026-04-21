from fastapi import APIRouter, Depends, HTTPException, status
import pymysql

from app.schemas import RatingCreate, RatingOut
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api", tags=["Ratings"])


@router.post("/ratings")
def submit_rating(
    req: RatingCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    # rate a seller (only buyers can do it, 1 per day)
    if current_user["role"] != "Buyer":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only buyers can submit ratings")

    with db.cursor() as cursor:
        cursor.execute("SELECT email FROM Seller WHERE email = %s", (req.seller_email,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Seller not found")

        # bidder must have a completed, paid transaction with this seller
        cursor.execute(
            """
            SELECT 1 FROM Transaction
            WHERE seller_email = %s
              AND buyer_email = %s
              AND payment_status = 'completed'
            LIMIT 1
            """,
            (req.seller_email, current_user["email"]),
        )
        if not cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only rate a seller after winning and paying for one of their auctions",
            )

        try:
            cursor.execute(
                """
                INSERT INTO Rating (bidder_email, seller_email, rating_date, rating, rating_desc)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (current_user["email"], req.seller_email, req.rating_date, req.rating, req.rating_desc),
            )
            cursor.execute(
                "UPDATE Seller SET avg_rating = (SELECT AVG(rating) FROM Rating WHERE seller_email = %s) "
                "WHERE email = %s",
                (req.seller_email, req.seller_email),
            )
            db.commit()
        except pymysql.err.IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="You already rated this seller on that date")
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    return {"detail": "Rating submitted successfully"}


@router.get("/sellers/{email}/ratings", response_model=list[RatingOut])
def get_seller_ratings(email: str, db=Depends(get_db)):
    # get all ratings for the seller with newest first
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT bidder_email, seller_email, rating_date, rating, rating_desc "
            "FROM Rating WHERE seller_email = %s ORDER BY rating_date DESC",
            (email,),
        )
        return cursor.fetchall()
