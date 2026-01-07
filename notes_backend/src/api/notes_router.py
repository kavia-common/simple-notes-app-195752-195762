"""Notes CRUD routes backed by SQLite."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Path, Query

from src.api.db import sqlite_connection, utc_now_iso
from src.api.models import NoteCreate, NoteOut, NoteUpdate, PaginatedNotes

router = APIRouter(prefix="/notes", tags=["notes"])


_SORT_FIELDS = {
    "created_date": "created_date",
    "modified_date": "modified_date",
    "title": "title",
    "id": "id",
}


def _row_to_note_out(row) -> NoteOut:
    """Convert sqlite3.Row to NoteOut."""
    return NoteOut(
        id=row["id"],
        title=row["title"],
        content=row["content"],
        created_date=row["created_date"],
        modified_date=row["modified_date"],
        deleted_date=row["deleted_date"],
    )


@router.get(
    "",
    response_model=PaginatedNotes,
    summary="List notes",
    description=(
        "List notes with pagination and sorting. Soft-deleted notes "
        "(deleted_date IS NOT NULL) are excluded."
    ),
    operation_id="list_notes",
)
# PUBLIC_INTERFACE
def list_notes(
    limit: int = Query(20, ge=1, le=200, description="Max number of notes to return."),
    offset: int = Query(0, ge=0, description="Number of notes to skip."),
    sort_by: Literal["created_date", "modified_date", "title", "id"] = Query(
        "modified_date", description="Field to sort by."
    ),
    sort_order: Literal["asc", "desc"] = Query(
        "desc", description="Sort direction."
    ),
) -> PaginatedNotes:
    """Return a paginated list of active notes."""
    sort_col = _SORT_FIELDS[sort_by]
    sort_dir = "ASC" if sort_order.lower() == "asc" else "DESC"

    with sqlite_connection() as conn:
        # Total count (active only)
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM notes WHERE deleted_date IS NULL"
        ).fetchone()["c"]

        rows = conn.execute(
            f"""
            SELECT id, title, content, created_date, modified_date, deleted_date
            FROM notes
            WHERE deleted_date IS NULL
            ORDER BY {sort_col} {sort_dir}
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()

    return PaginatedNotes(
        total=total,
        items=[_row_to_note_out(r) for r in rows],
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{note_id}",
    response_model=NoteOut,
    summary="Get note by ID",
    description="Fetch a single note by ID (404 if not found or soft-deleted).",
    operation_id="get_note",
)
# PUBLIC_INTERFACE
def get_note(
    note_id: int = Path(..., ge=1, description="Note ID."),
) -> NoteOut:
    """Get a single active note."""
    with sqlite_connection() as conn:
        row = conn.execute(
            """
            SELECT id, title, content, created_date, modified_date, deleted_date
            FROM notes
            WHERE id = ? AND deleted_date IS NULL
            """,
            (note_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Note not found")

    return _row_to_note_out(row)


@router.post(
    "",
    response_model=NoteOut,
    status_code=201,
    summary="Create note",
    description="Create a new note. created_date and modified_date are set by server.",
    operation_id="create_note",
)
# PUBLIC_INTERFACE
def create_note(payload: NoteCreate) -> NoteOut:
    """Create a new note."""
    now = utc_now_iso()

    with sqlite_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO notes (title, content, created_date, modified_date, deleted_date)
            VALUES (?, ?, ?, ?, NULL)
            """,
            (payload.title, payload.content, now, now),
        )
        note_id = cur.lastrowid
        conn.commit()

        row = conn.execute(
            """
            SELECT id, title, content, created_date, modified_date, deleted_date
            FROM notes
            WHERE id = ?
            """,
            (note_id,),
        ).fetchone()

    return _row_to_note_out(row)


@router.put(
    "/{note_id}",
    response_model=NoteOut,
    summary="Update note",
    description=(
        "Update note title/content and bump modified_date. "
        "Returns 404 if not found or soft-deleted."
    ),
    operation_id="update_note",
)
# PUBLIC_INTERFACE
def update_note(
    payload: NoteUpdate,
    note_id: int = Path(..., ge=1, description="Note ID."),
) -> NoteOut:
    """Update an existing active note."""
    if payload.title is None and payload.content is None:
        raise HTTPException(
            status_code=400, detail="At least one of title/content must be provided"
        )

    now = utc_now_iso()

    with sqlite_connection() as conn:
        existing = conn.execute(
            """
            SELECT id, title, content, created_date, modified_date, deleted_date
            FROM notes
            WHERE id = ? AND deleted_date IS NULL
            """,
            (note_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Note not found")

        new_title = payload.title if payload.title is not None else existing["title"]
        new_content = (
            payload.content if payload.content is not None else existing["content"]
        )

        conn.execute(
            """
            UPDATE notes
            SET title = ?, content = ?, modified_date = ?
            WHERE id = ?
            """,
            (new_title, new_content, now, note_id),
        )
        conn.commit()

        row = conn.execute(
            """
            SELECT id, title, content, created_date, modified_date, deleted_date
            FROM notes
            WHERE id = ?
            """,
            (note_id,),
        ).fetchone()

    return _row_to_note_out(row)


@router.delete(
    "/{note_id}",
    response_model=NoteOut,
    summary="Soft-delete note",
    description=(
        "Soft-delete a note by setting deleted_date (and modified_date) to now. "
        "Returns 404 if not found or already deleted."
    ),
    operation_id="delete_note",
)
# PUBLIC_INTERFACE
def delete_note(
    note_id: int = Path(..., ge=1, description="Note ID."),
) -> NoteOut:
    """Soft-delete a note."""
    now = utc_now_iso()

    with sqlite_connection() as conn:
        row = conn.execute(
            """
            SELECT id, title, content, created_date, modified_date, deleted_date
            FROM notes
            WHERE id = ? AND deleted_date IS NULL
            """,
            (note_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Note not found")

        conn.execute(
            """
            UPDATE notes
            SET deleted_date = ?, modified_date = ?
            WHERE id = ?
            """,
            (now, now, note_id),
        )
        conn.commit()

        updated = conn.execute(
            """
            SELECT id, title, content, created_date, modified_date, deleted_date
            FROM notes
            WHERE id = ?
            """,
            (note_id,),
        ).fetchone()

    return _row_to_note_out(updated)
