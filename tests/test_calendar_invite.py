"""Unit tests for CalendarInviteService."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from calendar_invite.models import CalendarInviteRequest, CalendarInviteResponse, Guest
from calendar_invite.service import CalendarInviteService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service() -> CalendarInviteService:
    return CalendarInviteService(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="sender@example.com",
        smtp_password="secret",
        use_tls=True,
    )


@pytest.fixture
def invite_request() -> CalendarInviteRequest:
    return CalendarInviteRequest(
        title="Team Sync",
        description="Weekly sync-up",
        location="https://meet.example.com/sync",
        start_time=datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 3, 15, 11, 0, 0, tzinfo=timezone.utc),
        organizer_name="Alice",
        organizer_email="alice@example.com",
        guests=[
            Guest(name="Bob", email="bob@example.com"),
            Guest(name="Carol", email="carol@example.com"),
        ],
    )


# ---------------------------------------------------------------------------
# ICS generation tests
# ---------------------------------------------------------------------------

class TestBuildIcs:
    def test_ics_contains_required_fields(self, service, invite_request):
        ics = service._build_ics(invite_request, "test-uid-123")
        assert "BEGIN:VCALENDAR" in ics
        assert "END:VCALENDAR" in ics
        assert "BEGIN:VEVENT" in ics
        assert "END:VEVENT" in ics

    def test_ics_uid(self, service, invite_request):
        uid = "unique-event-id"
        ics = service._build_ics(invite_request, uid)
        assert f"UID:{uid}" in ics

    def test_ics_summary(self, service, invite_request):
        ics = service._build_ics(invite_request, "uid")
        assert "SUMMARY:Team Sync" in ics

    def test_ics_dtstart_dtend(self, service, invite_request):
        ics = service._build_ics(invite_request, "uid")
        assert "DTSTART:20260315T100000Z" in ics
        assert "DTEND:20260315T110000Z" in ics

    def test_ics_organizer(self, service, invite_request):
        ics = service._build_ics(invite_request, "uid")
        assert "ORGANIZER;CN=Alice:mailto:alice@example.com" in ics

    def test_ics_attendees(self, service, invite_request):
        ics = service._build_ics(invite_request, "uid")
        assert "mailto:bob@example.com" in ics
        assert "mailto:carol@example.com" in ics

    def test_ics_location(self, service, invite_request):
        ics = service._build_ics(invite_request, "uid")
        assert "LOCATION:https://meet.example.com/sync" in ics

    def test_ics_method_request(self, service, invite_request):
        ics = service._build_ics(invite_request, "uid")
        assert "METHOD:REQUEST" in ics

    def test_ics_no_description(self, service, invite_request):
        invite_request.description = None
        ics = service._build_ics(invite_request, "uid")
        assert "DESCRIPTION:" in ics  # empty description is included


# ---------------------------------------------------------------------------
# Email body tests
# ---------------------------------------------------------------------------

class TestBuildEmailBody:
    def test_body_contains_guest_name(self, invite_request):
        guest = invite_request.guests[0]
        body = CalendarInviteService._build_email_body(invite_request, guest)
        assert "Bob" in body

    def test_body_contains_event_title(self, invite_request):
        guest = invite_request.guests[0]
        body = CalendarInviteService._build_email_body(invite_request, guest)
        assert "Team Sync" in body

    def test_body_contains_location(self, invite_request):
        guest = invite_request.guests[0]
        body = CalendarInviteService._build_email_body(invite_request, guest)
        assert "https://meet.example.com/sync" in body

    def test_body_contains_description(self, invite_request):
        guest = invite_request.guests[0]
        body = CalendarInviteService._build_email_body(invite_request, guest)
        assert "Weekly sync-up" in body

    def test_body_omits_location_when_none(self, invite_request):
        invite_request.location = None
        guest = invite_request.guests[0]
        body = CalendarInviteService._build_email_body(invite_request, guest)
        assert "Where:" not in body


# ---------------------------------------------------------------------------
# send_invites integration tests (SMTP mocked)
# ---------------------------------------------------------------------------

class TestSendInvites:
    @patch("calendar_invite.service.smtplib.SMTP")
    def test_all_guests_notified_on_success(self, mock_smtp_cls, service, invite_request):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp

        response = service.send_invites(invite_request)

        assert response.success is True
        assert set(response.guests_notified) == {"bob@example.com", "carol@example.com"}
        assert response.failed_guests == []

    @patch("calendar_invite.service.smtplib.SMTP")
    def test_failed_guest_recorded(self, mock_smtp_cls, service, invite_request):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp
        # Make sendmail raise for the first call only
        call_count = {"n": 0}

        def sendmail_side_effect(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Exception("SMTP error")

        mock_smtp.sendmail.side_effect = sendmail_side_effect

        response = service.send_invites(invite_request)

        assert len(response.failed_guests) == 1
        assert len(response.guests_notified) == 1
        assert response.success is False

    @patch("calendar_invite.service.smtplib.SMTP")
    def test_event_uid_in_response(self, mock_smtp_cls, service, invite_request):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp

        response = service.send_invites(invite_request)

        assert response.event_uid != ""
        assert len(response.event_uid) == 36  # UUID4 format

    @patch("calendar_invite.service.smtplib.SMTP")
    def test_smtp_starttls_called_when_tls_enabled(
        self, mock_smtp_cls, service, invite_request
    ):
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp

        service.send_invites(invite_request)

        assert mock_smtp.starttls.called

    @patch("calendar_invite.service.smtplib.SMTP")
    def test_smtp_starttls_not_called_when_tls_disabled(
        self, mock_smtp_cls, invite_request
    ):
        service_no_tls = CalendarInviteService(
            smtp_host="smtp.example.com",
            smtp_port=25,
            smtp_user="user",
            smtp_password="pass",
            use_tls=False,
        )
        mock_smtp = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_smtp

        service_no_tls.send_invites(invite_request)

        mock_smtp.starttls.assert_not_called()
