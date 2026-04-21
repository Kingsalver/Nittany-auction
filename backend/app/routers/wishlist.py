from fastapi import APIRouter, Depends, HTTPException
import pymysql.err
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/wishlist", tags=["wishlist"])


@router.get("")
def get_wishlist(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    if current_user["role"] != "Buyer":
        raise HTTPException(status_code=403, detail="Only buyers can access a wishlist")

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT w.product_id, w.date_time_added,
                   p.auction_title, p.reserve_price, p.photo_path,
                   p.seller_email, p.listing_status,
                   (SELECT COUNT(*) FROM Bid b WHERE b.product_id = p.product_id) AS bid_count
            FROM Watchlist w
            JOIN Product p ON p.product_id = w.product_id
            WHERE w.bidder_email = %s
            ORDER BY w.date_time_added DESC
            """,
            (current_user["email"],),
        )
        return cursor.fetchall()


@router.get("/{product_id}/check")
def check_wishlist(product_id: int, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    if current_user["role"] != "Buyer":
        return {"wishlisted": False}

    with db.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM Watchlist WHERE bidder_email = %s AND product_id = %s",
            (current_user["email"], product_id),
        )
        return {"wishlisted": cursor.fetchone() is not None}


@router.post("/{product_id}")
def add_to_wishlist(product_id: int, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    if current_user["role"] != "Buyer":
        raise HTTPException(status_code=403, detail="Only buyers can add to a wishlist")

    with db.cursor() as cursor:
        cursor.execute("SELECT product_id FROM Product WHERE product_id = %s", (product_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Product not found")

        try:
            cursor.execute(
                "INSERT INTO Watchlist (bidder_email, product_id) VALUES (%s, %s)",
                (current_user["email"], product_id),
            )
            db.commit()
        except pymysql.err.IntegrityError:
            pass  #if we're already in wishlist just treat as success

    return {"detail": "Added to wishlist"}


@router.delete("/{product_id}")
def remove_from_wishlist(product_id: int, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    if current_user["role"] != "Buyer":
        raise HTTPException(status_code=403, detail="Only buyers can modify a wishlist")

    with db.cursor() as cursor:
        cursor.execute(
            "DELETE FROM Watchlist WHERE bidder_email = %s AND product_id = %s",
            (current_user["email"], product_id),
        )
        db.commit()

    return {"detail": "Removed from wishlist"}
