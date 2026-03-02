"""FastAPI application entry point."""

import logging
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from calendar_invite.router import router as calendar_router

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="Calendar Invite Service",
    description="Send email calendar invitations (ICS) to guests.",
    version="1.0.0",
)

app.include_router(calendar_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
def health() -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})
