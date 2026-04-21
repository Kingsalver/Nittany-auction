from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.database import get_db
from app.schemas import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("", response_model=list[NotificationOut])
def get_unread_notifications(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    """Fetch all unread notifications for the current logged-in buyer"""
    if current_user["role"] != "Buyer":
        return [] # Only buyers get notifications in this schema
        
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT notification_id, bidder_email, product_id, notification_type, message, sent_at, is_read
            FROM Notification
            WHERE bidder_email = %s AND is_read = FALSE
            ORDER BY sent_at DESC
            """,
            (current_user["email"],)
        )
        return cursor.fetchall()
        
@router.patch("/{notification_id}/read")
def mark_notification_read(notification_id: int, current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    """Mark a notification as read"""
    with db.cursor() as cursor:
        # First verify it belongs to them
        cursor.execute("SELECT bidder_email FROM Notification WHERE notification_id = %s", (notification_id,))
        notif = cursor.fetchone()
        
        if not notif:
            raise HTTPException(status_code=404, detail="Notification not found")
            
        if notif["bidder_email"] != current_user["email"]:
            raise HTTPException(status_code=403, detail="Not authorized to read this notification")
            
        cursor.execute(
            "UPDATE Notification SET is_read = TRUE WHERE notification_id = %s",
            (notification_id,)
        )
        db.commit()
        
    return {"detail": "Notification marked as read"}
