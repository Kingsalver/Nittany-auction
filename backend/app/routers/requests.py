"""
routers/requests.py — HelpDesk request management endpoints.

Request flow:
  - Any logged-in user can submit a request (POST /api/requests)
  - HelpDesk staff can view all requests (GET /api/requests)
  - HelpDesk staff can claim a request, assigning it to themselves (PATCH /api/requests/{id}/claim)
  - HelpDesk staff can mark a request as complete (PATCH /api/requests/{id}/complete)
"""

from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.auth import get_current_user
from app.schemas import RequestCreate

router = APIRouter(prefix="/api", tags=["Requests"])


@router.post("/requests")
def submit_request(req: RequestCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Any logged-in user can submit a request to HelpDesk."""
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
    """HelpDesk staff can see all requests. Bidders can see their own."""
    with db.cursor() as cursor:
        if current_user["role"] == "HelpDesk":
            # HelpDesk sees everything
            cursor.execute(
                """
                SELECT request_id, sender_email, helpdesk_staff_email,
                       request_type, request_desc, request_status, date_submitted
                FROM Request
                ORDER BY request_status ASC, date_submitted DESC
                """
            )
        else:
            # Regular users only see their own requests
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
    """HelpDesk staff claims an unassigned request, assigning it to themselves."""
    if current_user["role"] != "HelpDesk":
        raise HTTPException(status_code=403, detail="Only HelpDesk staff can claim requests")

    with db.cursor() as cursor:
        # Make sure it exists and is still unassigned
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
    """HelpDesk staff marks a request as complete (status = 1)."""
    if current_user["role"] != "HelpDesk":
        raise HTTPException(status_code=403, detail="Only HelpDesk staff can complete requests")

    with db.cursor() as cursor:
        cursor.execute(
            "SELECT request_status FROM Request WHERE request_id = %s",
            (request_id,)
        )
        req = cursor.fetchone()

        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        if req["request_status"] == 1:
            raise HTTPException(status_code=400, detail="Request is already completed")

        cursor.execute(
            "UPDATE Request SET request_status = 1 WHERE request_id = %s",
            (request_id,),
        )
    db.commit()
    return {"detail": "Request marked as complete"}
