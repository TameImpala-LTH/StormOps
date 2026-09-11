"""Canonical Conversational AI chat endpoint with optional authenticated persistence."""

import logging
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.query import QueryRequest, QueryResponse
from app.services.query_service import SESSION_CONTEXT, query_service


logger = logging.getLogger(__name__)

router = APIRouter()


def _generate_conversation_title(query_text: str, location_name: Optional[str] = None, period_label: Optional[str] = None) -> str:
    """Generate a clean, deterministic short title without invoking an LLM."""
    clean = query_text.strip().rstrip("?!.").strip()
    if location_name and period_label:
        return f"{location_name} · {period_label.title()}"
    elif location_name:
        return f"{location_name} weather"
    return clean[:40] if len(clean) > 40 else clean


@router.post("", response_model=QueryResponse)
@router.post("/", response_model=QueryResponse)
async def chat_query(
    request: QueryRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Canonical conversational weather intelligence chat endpoint.

    Processes natural language weather questions with session context, extracts structured intent
    via LLM (with deterministic fallback), resolves location coordinates, retrieves real
    meteorological data, and returns a grounded natural language response or clarification.

    If the request is authenticated, persists the conversation and messages to PostgreSQL.
    If database persistence fails, logs server-side and continues weather answering seamlessly.
    """
    sess_id = request.session_id or "default"

    # Pre-seed session context from existing conversation if continuing with an authenticated session
    if current_user and request.session_id and len(request.session_id) == 36:
        if sess_id not in SESSION_CONTEXT or not SESSION_CONTEXT[sess_id].get("location"):
            try:
                conv_record = db.query(Conversation).filter(
                    Conversation.id == request.session_id,
                    Conversation.user_id == current_user.id,
                ).first()
                if conv_record:
                    if sess_id not in SESSION_CONTEXT:
                        SESSION_CONTEXT[sess_id] = {}
                    if conv_record.location_name and not SESSION_CONTEXT[sess_id].get("location"):
                        from app.services.geocoding_service import geocoding_service
                        geo = await geocoding_service.geocode_location(conv_record.location_name)
                        if geo:
                            SESSION_CONTEXT[sess_id]["location"] = geo
                    # Pre-seed last user query for entity continuity
                    if "last_query" not in SESSION_CONTEXT[sess_id]:
                        user_messages = [m for m in conv_record.messages if m.role == "user"]
                        if user_messages:
                            from app.schemas.query import ExtractedQueryInfo
                            last_msg_text = user_messages[-1].content
                            # Build baseline query info for context fallback
                            SESSION_CONTEXT[sess_id]["last_query"] = ExtractedQueryInfo(
                                raw_query=last_msg_text,
                                extracted_location=conv_record.location_name or "",
                                intent="weather_information",
                            )
            except Exception as e:
                logger.debug(f"Could not pre-seed location context for {request.session_id}: {e}")

    response: QueryResponse = await query_service.process_query(
        request.message,
        session_id=sess_id,
        device_location=request.location,
        language=request.language,
    )

    # If authenticated, persist conversation and message records
    if current_user:
        try:
            active_session = db
            close_session_at_end = False
            if active_session is None:
                from app.db.session import SessionLocal
                if SessionLocal is not None:
                    active_session = SessionLocal()
                    close_session_at_end = True

            if active_session is not None:
                try:
                    # Look up active conversation by session_id if it corresponds to an existing conversation
                    conv = None
                    if request.session_id and len(request.session_id) == 36:
                        conv = active_session.query(Conversation).filter(
                            Conversation.id == request.session_id,
                            Conversation.user_id == current_user.id,
                        ).first()

                    loc_name = response.location.name if response.location else None
                    period_lbl = response.period_weather.period_label if response.period_weather else None

                    if not conv:
                        title = _generate_conversation_title(request.message, loc_name, period_lbl)
                        conv = Conversation(
                            user_id=current_user.id,
                            title=title,
                            location_name=loc_name,
                        )
                        active_session.add(conv)
                        active_session.commit()
                        active_session.refresh(conv)

                    # Persist user query message
                    user_msg = Message(
                        conversation_id=conv.id,
                        role="user",
                        content=request.message,
                    )
                    active_session.add(user_msg)

                    # Persist assistant answer message (lightweight content without raw weather duplication)
                    assistant_msg = Message(
                        conversation_id=conv.id,
                        role="assistant",
                        content=response.summary,
                    )
                    active_session.add(assistant_msg)

                    # Update conversation timestamp & location
                    if loc_name and not conv.location_name:
                        conv.location_name = loc_name
                    active_session.commit()

                    # Attach persistent conversation id to response session_id for frontend tracking
                    response.session_id = conv.id
                finally:
                    if close_session_at_end:
                        active_session.close()
        except Exception as exc:
            logger.warning(f"Failed to persist authenticated conversation: {exc}")
            # Do NOT crash weather response

    return response



