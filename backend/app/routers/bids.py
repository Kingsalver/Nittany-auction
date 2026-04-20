from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.database import get_db
from app.schemas import BidCreate, BidOut

router = APIRouter(prefix="/api", tags=["bids"])


@router.post("/products/{product_id}/bids", response_model=dict)
def place_bid(
    product_id: int,
    bid: BidCreate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    if current_user["role"] != "Buyer":
        raise HTTPException(status_code=403, detail="Only bidders can place bids")

    with db.cursor() as cursor:
        # Fetch listing state + current highest bid + last bidder in one query
        cursor.execute(
            """
            SELECT p.product_id, p.seller_email, p.listing_status, p.reserve_price,
                   p.max_bids,
                   COUNT(b.bid_id) AS bid_count,
                   MAX(b.bid_price) AS highest_bid,
                   (SELECT bidder_email FROM Bid
                    WHERE product_id = %s
                    ORDER BY bid_timestamp DESC LIMIT 1) AS last_bidder
            FROM Product p
            LEFT JOIN Bid b ON b.product_id = p.product_id
            WHERE p.product_id = %s
            GROUP BY p.product_id
            """,
            (product_id, product_id),
        )
        listing = cursor.fetchone()

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing["listing_status"] != "active":
        raise HTTPException(status_code=422, detail="Listing is not active")
    if listing["seller_email"] == current_user["email"]:
        raise HTTPException(status_code=422, detail="Sellers cannot bid on their own listings")
    if listing["last_bidder"] == current_user["email"]:
        raise HTTPException(status_code=422, detail="Cannot bid twice in a row")

    min_bid = (
        float(listing["highest_bid"]) + 1.00
        if listing["highest_bid"] is not None
        else float(listing["reserve_price"])
    )
    if bid.bid_price < min_bid:
        raise HTTPException(
            status_code=422,
            detail=f"Bid must be at least ${min_bid:.2f}",
        )

    try:
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO Bid (product_id, seller_email, bidder_email, bid_price) VALUES (%s, %s, %s, %s)",
                (product_id, listing["seller_email"], current_user["email"], bid.bid_price),
            )
            new_bid_count = listing["bid_count"] + 1

            if new_bid_count >= listing["max_bids"]:
                cursor.execute(
                    "UPDATE Product SET listing_status = 'sold' WHERE product_id = %s",
                    (product_id,),
                )
                cursor.execute(
                    """
                    INSERT INTO Transactions (product_id, seller_email, buyer_email, payment_date, payment)
                    VALUES (%s, %s, %s, CURDATE(), %s)
                    """,
                    (product_id, listing["seller_email"], current_user["email"], bid.bid_price),
                )

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": "Bid placed successfully",
        "product_id": product_id,
        "bid_price": bid.bid_price,
        "auction_closed": new_bid_count >= listing["max_bids"],
    }


@router.get("/products/{product_id}/bids", response_model=list[BidOut])
def get_bids(product_id: int, db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT bid_id, product_id, bidder_email, bid_price, bid_timestamp
            FROM Bid
            WHERE product_id = %s
            ORDER BY bid_timestamp DESC
            """,
            (product_id,),
        )
        return cursor.fetchall()
