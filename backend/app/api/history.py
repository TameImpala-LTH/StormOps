"""Personal conversation history router for authenticated consumers."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.history import ConversationDetail, ConversationSummary

router = APIRouter()


@router.get("", response_model=List[ConversationSummary])
@router.get("/", response_model=List[ConversationSummary])
def list_user_history(
    limit: int = Query(50, ge=1, le=100, description="Max number of conversations to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve previous WeatherGPT conversations belonging strictly to the authenticated user.

    Results are ordered by most recently updated first, bounded by limit and offset.
    """
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    summaries = []
    for c in conversations:
        # Extract last user message and last assistant message for timeline preview
        last_query = None
        last_answer = None
        for m in reversed(c.messages):
            if not last_query and m.role == "user":
                last_query = m.content
            if not last_answer and m.role == "assistant":
                last_answer = m.content
            if last_query and last_answer:
                break
        summaries.append(
            ConversationSummary(
                id=c.id,
                title=c.title,
                location_name=c.location_name,
                created_at=c.created_at,
                updated_at=c.updated_at,
                last_query=last_query,
                last_answer=last_answer,
            )
        )
    return summaries



@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation_detail(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a specific historical conversation with its messages.

    Enforces strict ownership: returns 404 if conversation does not exist or belongs to another user.
    """
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    return ConversationDetail.model_validate(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation belonging strictly to the authenticated user."""
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    db.delete(conversation)
    db.commit()
    return None
