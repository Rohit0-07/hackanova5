"""
Email Notification API Routes — register/unregister email subscriptions for session notifications.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from loguru import logger

from app.services.email_service import register_email, get_email_for_session, unregister_email

router = APIRouter()


class EmailSubscriptionRequest(BaseModel):
    session_id: str = Field(..., description="Session ID to subscribe to")
    email: str = Field(..., description="Email address to notify")


class EmailSubscriptionResponse(BaseModel):
    success: bool
    message: str
    session_id: str
    email: Optional[str] = None


@router.post(
    "/register",
    response_model=EmailSubscriptionResponse,
    tags=["Notifications"],
    summary="Register email for session completion notification"
)
async def register_email_notification(
    request: EmailSubscriptionRequest,
) -> EmailSubscriptionResponse:
    """
    Register an email address to receive a notification when the given session
    completes analysis. The email will include a direct backlink to the session.
    """
    try:
        # Basic email format validation
        if "@" not in request.email or "." not in request.email.split("@")[-1]:
            raise HTTPException(status_code=422, detail="Invalid email address format")

        register_email(request.session_id, request.email)
        logger.info(f"Email registered: {request.email} → session {request.session_id}")

        return EmailSubscriptionResponse(
            success=True,
            message=f"You'll receive an email at {request.email} when the analysis completes.",
            session_id=request.session_id,
            email=request.email,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/unregister/{session_id}",
    response_model=EmailSubscriptionResponse,
    tags=["Notifications"],
    summary="Unregister email notification for a session"
)
async def unregister_email_notification(session_id: str) -> EmailSubscriptionResponse:
    """Remove email subscription for a session."""
    try:
        email = get_email_for_session(session_id)
        unregister_email(session_id)
        return EmailSubscriptionResponse(
            success=True,
            message="Email notification removed.",
            session_id=session_id,
            email=email,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/status/{session_id}",
    tags=["Notifications"],
    summary="Check if email is registered for a session"
)
async def get_notification_status(session_id: str):
    """Check whether an email is registered for the given session."""
    email = get_email_for_session(session_id)
    return {
        "session_id": session_id,
        "subscribed": email is not None,
        "email": email,
    }
