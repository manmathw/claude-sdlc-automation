"""Pydantic models for calendar invite requests and responses."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class Guest(BaseModel):
    """Represents an invited guest."""

    name: str = Field(..., description="Full name of the guest")
    email: EmailStr = Field(..., description="Email address of the guest")


class CalendarInviteRequest(BaseModel):
    """Request body for creating and sending a calendar invite."""

    title: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    location: Optional[str] = Field(None, description="Event location or meeting URL")
    start_time: datetime = Field(..., description="Event start time (UTC)")
    end_time: datetime = Field(..., description="Event end time (UTC)")
    organizer_name: str = Field(..., description="Name of the event organizer")
    organizer_email: EmailStr = Field(..., description="Email of the event organizer")
    guests: List[Guest] = Field(..., min_items=1, description="List of guests to invite")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Project Kickoff Meeting",
                "description": "Initial kickoff for Q2 project planning",
                "location": "https://meet.example.com/kickoff",
                "start_time": "2026-03-15T10:00:00Z",
                "end_time": "2026-03-15T11:00:00Z",
                "organizer_name": "Alice Smith",
                "organizer_email": "alice@example.com",
                "guests": [
                    {"name": "Bob Jones", "email": "bob@example.com"},
                    {"name": "Carol White", "email": "carol@example.com"},
                ],
            }
        }


class CalendarInviteResponse(BaseModel):
    """Response returned after sending calendar invites."""

    success: bool = Field(..., description="Whether invites were sent successfully")
    event_uid: str = Field(..., description="Unique identifier for the calendar event")
    guests_notified: List[str] = Field(..., description="List of notified guest emails")
    failed_guests: List[str] = Field(
        default_factory=list, description="Guest emails that failed to receive invite"
    )
    message: str = Field(..., description="Human-readable status message")
