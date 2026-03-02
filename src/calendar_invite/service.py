"""Calendar invite service: ICS generation and email delivery."""

import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Tuple

from .models import CalendarInviteRequest, CalendarInviteResponse, Guest

logger = logging.getLogger(__name__)


class CalendarInviteService:
    """Handles ICS creation and email delivery of calendar invitations."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        use_tls: bool = True,
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_invites(self, request: CalendarInviteRequest) -> CalendarInviteResponse:
        """Generate an ICS file and email it to every guest.

        Args:
            request: Validated calendar invite request.

        Returns:
            CalendarInviteResponse with delivery results.
        """
        event_uid = str(uuid.uuid4())
        ics_content = self._build_ics(request, event_uid)

        notified: List[str] = []
        failed: List[str] = []

        for guest in request.guests:
            try:
                self._send_email(request, guest, ics_content)
                notified.append(guest.email)
                logger.info("Invite sent to %s", guest.email)
            except Exception as exc:
                failed.append(guest.email)
                logger.error("Failed to send invite to %s: %s", guest.email, exc)

        success = len(notified) > 0 and len(failed) == 0
        msg = (
            f"Invites sent to {len(notified)} guest(s)."
            if not failed
            else f"Sent to {len(notified)}, failed for {len(failed)} guest(s)."
        )

        return CalendarInviteResponse(
            success=success,
            event_uid=event_uid,
            guests_notified=notified,
            failed_guests=failed,
            message=msg,
        )

    # ------------------------------------------------------------------
    # ICS generation
    # ------------------------------------------------------------------

    def _build_ics(self, request: CalendarInviteRequest, event_uid: str) -> str:
        """Produce an RFC 5545-compliant iCalendar string.

        Args:
            request: The calendar invite request.
            event_uid: Globally unique identifier for the event.

        Returns:
            ICS file content as a string.
        """
        now = datetime.now(timezone.utc)
        dtstamp = self._fmt_dt(now)
        dtstart = self._fmt_dt(request.start_time)
        dtend = self._fmt_dt(request.end_time)

        attendees = "\n".join(
            f"ATTENDEE;CN={guest.name};ROLE=REQ-PARTICIPANT;RSVP=TRUE:mailto:{guest.email}"
            for guest in request.guests
        )

        description = (request.description or "").replace("\n", "\\n")
        location = request.location or ""

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//CalendarInviteService//EN",
            "METHOD:REQUEST",
            "BEGIN:VEVENT",
            f"UID:{event_uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{request.title}",
            f"DESCRIPTION:{description}",
            f"LOCATION:{location}",
            f"ORGANIZER;CN={request.organizer_name}:mailto:{request.organizer_email}",
            attendees,
            "STATUS:CONFIRMED",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
        return "\r\n".join(lines)

    @staticmethod
    def _fmt_dt(dt: datetime) -> str:
        """Format a datetime as iCalendar UTC timestamp."""
        return dt.strftime("%Y%m%dT%H%M%SZ")

    # ------------------------------------------------------------------
    # Email delivery
    # ------------------------------------------------------------------

    def _send_email(
        self,
        request: CalendarInviteRequest,
        guest: Guest,
        ics_content: str,
    ) -> None:
        """Send a single calendar invite email with ICS attachment.

        Args:
            request: The invite request (provides event metadata).
            guest: The recipient.
            ics_content: The ICS file content.

        Raises:
            smtplib.SMTPException: On SMTP delivery failure.
        """
        msg = MIMEMultipart("mixed")
        msg["Subject"] = f"Invitation: {request.title}"
        msg["From"] = f"{request.organizer_name} <{request.organizer_email}>"
        msg["To"] = f"{guest.name} <{guest.email}>"

        # Plain-text body
        body = self._build_email_body(request, guest)
        msg.attach(MIMEText(body, "plain"))

        # ICS attachment
        ics_part = MIMEBase("text", "calendar", method="REQUEST", name="invite.ics")
        ics_part.set_payload(ics_content.encode("utf-8"))
        encoders.encode_base64(ics_part)
        ics_part.add_header("Content-Disposition", "attachment", filename="invite.ics")
        msg.attach(ics_part)

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.use_tls:
                server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(request.organizer_email, guest.email, msg.as_string())

    @staticmethod
    def _build_email_body(request: CalendarInviteRequest, guest: Guest) -> str:
        """Construct the plain-text body for the invitation email."""
        start = request.start_time.strftime("%A, %B %d %Y at %H:%M UTC")
        end = request.end_time.strftime("%H:%M UTC")
        lines = [
            f"Hi {guest.name},",
            "",
            f"You are invited to: {request.title}",
            f"When: {start} – {end}",
        ]
        if request.location:
            lines.append(f"Where: {request.location}")
        if request.description:
            lines.extend(["", request.description])
        lines.extend(
            [
                "",
                "Please find the calendar invite attached.",
                "",
                f"Regards,",
                f"{request.organizer_name}",
            ]
        )
        return "\n".join(lines)
