"""Health check API route."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint. Returns application status."""
    return {
        "status": "healthy",
        "service": "weathergpt-backend",
    }
