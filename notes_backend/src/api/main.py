"""FastAPI application entrypoint for the notes backend.

Provides:
- Health check endpoint
- Notes CRUD endpoints (SQLite-backed)
- Permissive CORS for local/dev integration with the React frontend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.notes_router import router as notes_router

openapi_tags = [
    {
        "name": "health",
        "description": "Service health and basic diagnostics.",
    },
    {
        "name": "notes",
        "description": "CRUD operations for notes (SQLite-backed, soft-delete).",
    },
]

app = FastAPI(
    title="Simple Notes API",
    description="Backend API for a simple notes app (FastAPI + SQLite).",
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# Keep permissive CORS as requested.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notes_router)


@app.get(
    "/",
    tags=["health"],
    summary="Health check",
    description="Simple health check endpoint for container orchestration.",
    operation_id="health_check",
)
# PUBLIC_INTERFACE
def health_check():
    """Return basic service health status."""
    return {"message": "Healthy"}
