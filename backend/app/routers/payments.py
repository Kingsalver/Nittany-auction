from fastapi import APIRouter, Depends, HTTPException, status
import pymysql

from app.auth import get_current_user
from app.database import get_db
from app.schemas import CreditCardDB

router = APIRouter(prefix="/api", tags=["Payments"])


@router.get("/credit-cards")
def get_credit_cards(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    if current_user["role"] != "Buyer":
        raise HTTPException(status_code=403, detail="Only buyers have credit cards")
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT credit_card_num, card_type, expire_month, expire_year FROM CreditCard WHERE owner_email = %s",
            (current_user["email"],),
        )
        return cursor.fetchall()


@router.post("/credit-cards", status_code=status.HTTP_201_CREATED)
def add_credit_card(card: CreditCardDB, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    if current_user["role"] != "Buyer":
        raise HTTPException(status_code=403, detail="Only buyers can add credit cards")
    try:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO CreditCard (credit_card_num, card_type, expire_month, expire_year, security_code, owner_email)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (card.credit_card_num, card.card_type, card.expire_month, card.expire_year,
                 card.security_code, current_user["email"]),
            )
        db.commit()
    except pymysql.err.IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This card number is already saved")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    return {"detail": "Credit card added"}


@router.get("/transactions/pending")
def get_pending_transactions(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    if current_user["role"] != "Buyer":
        raise HTTPException(status_code=403, detail="Only buyers have transactions")
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT t.transaction_id, t.product_id, t.seller_email, t.buyer_email,
                   t.payment, t.payment_date, t.payment_status,
                   p.auction_title
            FROM Transaction t
            JOIN Product p ON t.product_id = p.product_id
            WHERE t.buyer_email = %s AND t.payment_status = 'pending'
            ORDER BY t.transaction_id DESC
            """,
            (current_user["email"],),
        )
        return cursor.fetchall()


@router.post("/products/{product_id}/pay")
def pay_for_auction(
    product_id: int,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    if current_user["role"] != "Buyer":
        raise HTTPException(status_code=403, detail="Only buyers can make payments")

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT transaction_id, seller_email, payment, payment_status
            FROM Transaction
            WHERE product_id = %s AND buyer_email = %s
            LIMIT 1
            """,
            (product_id, current_user["email"]),
        )
        txn = cursor.fetchone()

    if not txn:
        raise HTTPException(status_code=404, detail="No transaction found for this auction")
    if txn["payment_status"] == "completed":
        raise HTTPException(status_code=400, detail="This auction has already been paid for")

    try:
        with db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE Transaction
                SET payment_status = 'completed', payment_date = CURDATE()
                WHERE transaction_id = %s
                """,
                (txn["transaction_id"],),
            )
            cursor.execute(
                "UPDATE Seller SET balance = balance + %s WHERE email = %s",
                (txn["payment"], txn["seller_email"]),
            )
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return {"detail": "Payment completed successfully", "amount": float(txn["payment"])}
