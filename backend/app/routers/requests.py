# endpoints for helpdesk requests
# users can make requests and helpdesk can claim or finish them

from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.auth import get_current_user
from app.schemas import RequestCreate

router = APIRouter(prefix="/api", tags=["Requests"])


@router.post("/requests")
def submit_request(req: RequestCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    # let any logged in user make a request
    with db.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO Request (sender_email, request_type, request_desc)
            VALUES (%s, %s, %s)
            """,
            (current_user["email"], req.request_type, req.request_desc),
        )
    db.commit()
    return {"detail": "Request submitted successfully"}


@router.get("/requests")
def get_requests(current_user=Depends(get_current_user), db=Depends(get_db)):
    # helpdesk sees everything, users just see their own requests
    with db.cursor() as cursor:
        if current_user["role"] == "HelpDesk":
            cursor.execute(
                """
                SELECT request_id, sender_email, helpdesk_staff_email,
                       request_type, request_desc, request_status, date_submitted
                FROM Request
                ORDER BY request_status ASC, date_submitted DESC
                """
            )
        else:
            cursor.execute(
                """
                SELECT request_id, sender_email, helpdesk_staff_email,
                       request_type, request_desc, request_status, date_submitted
                FROM Request
                WHERE sender_email = %s
                ORDER BY date_submitted DESC
                """,
                (current_user["email"],),
            )
        return cursor.fetchall()


@router.patch("/requests/{request_id}/claim")
def claim_request(request_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    # helpdesk staff assigns a request to themselves
    if current_user["role"] != "HelpDesk":
        raise HTTPException(status_code=403, detail="Only HelpDesk staff can claim requests")

    with db.cursor() as cursor:
        cursor.execute(
            "SELECT helpdesk_staff_email, request_status FROM Request WHERE request_id = %s",
            (request_id,)
        )
        req = cursor.fetchone()

        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        if req["request_status"] == 1:
            raise HTTPException(status_code=400, detail="Request is already completed")

        cursor.execute(
            "UPDATE Request SET helpdesk_staff_email = %s WHERE request_id = %s",
            (current_user["email"], request_id),
        )
    db.commit()
    return {"detail": "Request claimed successfully"}


@router.patch("/requests/{request_id}/complete")
def complete_request(request_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    # mark request as done and if it's a seller request, add them to the seller table
    import json as _json

    if current_user["role"] != "HelpDesk":
        raise HTTPException(status_code=403, detail="Only HelpDesk staff can complete requests")

    with db.cursor() as cursor:
        cursor.execute(
            "SELECT request_status, request_type, request_desc, sender_email FROM Request WHERE request_id = %s",
            (request_id,)
        )
        req = cursor.fetchone()

        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        if req["request_status"] == 1:
            raise HTTPException(status_code=400, detail="Request is already completed")

        # handle become_a_seller request and add to db
        if req["request_type"] == "BecomeASeller":
            try:
                desc = _json.loads(req["request_desc"] or "{}")
                routing = desc.get("bank_routing_number")
                account = desc.get("bank_account_number")
            except Exception:
                routing, account = None, None

            cursor.execute("SELECT email FROM Seller WHERE email = %s", (req["sender_email"],))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO Seller (email, bank_routing_number, bank_account_number, balance) VALUES (%s, %s, %s, 0.00)",
                    (req["sender_email"], routing, account)
                )

        cursor.execute(
            "UPDATE Request SET request_status = 1 WHERE request_id = %s",
            (request_id,),
        )
    db.commit()
    return {"detail": "Request marked as complete"}
