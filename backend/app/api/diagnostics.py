"""Diagnostic endpoints for server-side connectivity and provider checks."""

import time
from typing import Any, Dict
import httpx
from fastapi import APIRouter

router = APIRouter()


@router.get("/open-meteo")
@router.get("/open-meteo/")
async def diagnose_open_meteo() -> Dict[str, Any]:
    """Execute a single direct HTTP GET to Open-Meteo to diagnose connectivity and headers."""
    target_url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=22.56263&longitude=88.36304&current=temperature_2m&timezone=auto"
    )
    start_time = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(target_url)
            elapsed_seconds = time.perf_counter() - start_time
            body_sample = response.text[:1000] if response.text else ""
            return {
                "status_code": response.status_code,
                "elapsed_seconds": round(elapsed_seconds, 3),
                "headers": dict(response.headers),
                "body": body_sample,
            }
    except Exception as exc:
        elapsed_seconds = time.perf_counter() - start_time
        return {
            "status_code": 500,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "error": str(exc),
            "headers": {},
            "body": "",
        }
