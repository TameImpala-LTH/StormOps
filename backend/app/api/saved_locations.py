"""User-owned saved / favorite locations router."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.saved_location import SavedLocation
from app.models.user import User
from app.schemas.saved_location import SavedLocationCreate, SavedLocationResponse

router = APIRouter()


@router.get("", response_model=List[SavedLocationResponse])
@router.get("/", response_model=List[SavedLocationResponse])
def list_saved_locations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all locations saved/starred by the currently authenticated user."""
    locations = (
        db.query(SavedLocation)
        .filter(SavedLocation.user_id == current_user.id)
        .order_by(SavedLocation.created_at.desc())
        .all()
    )
    return [SavedLocationResponse.model_validate(loc) for loc in locations]


@router.post("", response_model=SavedLocationResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=SavedLocationResponse, status_code=status.HTTP_201_CREATED)
def create_saved_location(
    payload: SavedLocationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a favorite location for the currently authenticated user.

    Prevents duplicate saves of the same coordinates by the same user.
    """
    # Round coordinates to 4 decimals (~11m precision) to avoid floating point duplication
    lat = round(payload.latitude, 4)
    lon = round(payload.longitude, 4)

    existing = (
        db.query(SavedLocation)
        .filter(
            SavedLocation.user_id == current_user.id,
            SavedLocation.latitude == lat,
            SavedLocation.longitude == lon,
        )
        .first()
    )
    if existing:
        return SavedLocationResponse.model_validate(existing)

    new_location = SavedLocation(
        user_id=current_user.id,
        name=payload.name.strip(),
        latitude=lat,
        longitude=lon,
        country=payload.country.strip() if payload.country else None,
    )
    db.add(new_location)
    try:
        db.commit()
        db.refresh(new_location)
    except IntegrityError:
        db.rollback()
        existing_after = (
            db.query(SavedLocation)
            .filter(
                SavedLocation.user_id == current_user.id,
                SavedLocation.latitude == lat,
                SavedLocation.longitude == lon,
            )
            .first()
        )
        if existing_after:
            return SavedLocationResponse.model_validate(existing_after)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not save location.",
        )

    return SavedLocationResponse.model_validate(new_location)


@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_location(
    location_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a saved location belonging strictly to the authenticated user."""
    location = (
        db.query(SavedLocation)
        .filter(
            SavedLocation.id == location_id,
            SavedLocation.user_id == current_user.id,
        )
        .first()
    )
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved location not found.",
        )

    db.delete(location)
    db.commit()
    return None
