"""FastAPI router for calendar invite endpoints."""

import logging
import os

from fastapi import APIRouter, HTTPException

from .models import CalendarInviteRequest, CalendarInviteResponse
from .service import CalendarInviteService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calendar-invites", tags=["Calendar Invites"])


def _get_service() -> CalendarInviteService:
    """Construct CalendarInviteService from environment variables."""
    return CalendarInviteService(
        smtp_host=os.environ["SMTP_HOST"],
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_user=os.environ["SMTP_USER"],
        smtp_password=os.environ["SMTP_PASSWORD"],
        use_tls=os.environ.get("SMTP_USE_TLS", "true").lower() == "true",
    )


@router.post(
    "/send",
    response_model=CalendarInviteResponse,
    summary="Send calendar invites to guests",
    description=(
        "Creates an ICS calendar event and sends email invitations "
        "with the calendar file attached to all listed guests."
    ),
)
def send_calendar_invites(request: CalendarInviteRequest) -> CalendarInviteResponse:
    """Send a calendar invite to all guests in the request.

    Args:
        request: Event details and guest list.

    Returns:
        Delivery summary including successes and failures.
    """
    try:
        service = _get_service()
        return service.send_invites(request)
    except KeyError as exc:
        logger.error("Missing SMTP configuration: %s", exc)
        raise HTTPException(
            status_code=500,
            detail=f"Server misconfiguration: missing environment variable {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error sending invites: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to send calendar invites. Please try again later.",
        ) from exc
