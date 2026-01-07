"""Pydantic models for the Notes API."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class NoteBase(BaseModel):
    """Shared fields for note payloads."""

    title: str = Field(..., description="Human-friendly note title.")
    content: str = Field(..., description="Main note content/body.")


class NoteCreate(NoteBase):
    """Payload for creating a note."""


class NoteUpdate(BaseModel):
    """Payload for updating a note.

    Both fields are optional; at least one should be provided by the client.
    """

    title: Optional[str] = Field(None, description="New note title.")
    content: Optional[str] = Field(None, description="New note content/body.")


class NoteOut(NoteBase):
    """Note returned by the API."""

    id: int = Field(..., description="Note ID (auto-increment).")
    created_date: str = Field(..., description="ISO-8601 UTC timestamp when created.")
    modified_date: str = Field(
        ..., description="ISO-8601 UTC timestamp when last modified."
    )
    deleted_date: Optional[str] = Field(
        None, description="ISO-8601 UTC timestamp when soft-deleted (null if active)."
    )


class PaginatedNotes(BaseModel):
    """Paginated response of notes list."""

    total: int = Field(..., description="Total number of matching notes.")
    items: List[NoteOut] = Field(..., description="Notes for this page.")
    limit: int = Field(..., description="Page size used for the query.")
    offset: int = Field(..., description="Offset used for the query.")
