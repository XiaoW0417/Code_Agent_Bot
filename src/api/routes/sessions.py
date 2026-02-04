"""
Session management endpoints.
Enhanced with auto-naming, search, export, and tagging features.
"""
import logging
import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.infra.database.connection import get_db
from src.infra.database.models import User, Session as ChatSession, Message
from src.infra.database.repositories import SessionRepository, MessageRepository
from src.infra.auth.dependencies import get_current_active_user
from src.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class SessionCreateRequest(BaseModel):
    """Create session request."""
    title: str = Field(default="New Chat", max_length=200)
    model_name: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = Field(default_factory=list)


class SessionUpdateRequest(BaseModel):
    """Update session request."""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    model_name: Optional[str] = Field(None, max_length=100)
    is_archived: Optional[bool] = None
    is_pinned: Optional[bool] = None
    tags: Optional[List[str]] = None


class MessageResponse(BaseModel):
    """Message response."""
    id: str
    role: str
    content: str
    tool_call_id: Optional[str] = None
    tool_calls: Optional[list] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    """Session response."""
    id: str
    title: str
    description: Optional[str] = None
    model_name: str
    is_active: bool
    is_archived: bool
    is_pinned: bool = False
    tags: List[str] = []
    total_tokens_used: int
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = None
    last_message_preview: Optional[str] = None

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    """Session detail with messages."""
    messages: List[MessageResponse] = []


class SessionListResponse(BaseModel):
    """Session list response."""
    sessions: List[SessionResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class GenerateTitleRequest(BaseModel):
    """Request to generate title for a session."""
    session_id: str


class GenerateTitleResponse(BaseModel):
    """Response with generated title."""
    title: str
    description: Optional[str] = None


class SessionExportResponse(BaseModel):
    """Exported session data."""
    session: SessionResponse
    messages: List[MessageResponse]
    exported_at: datetime


class SearchRequest(BaseModel):
    """Search sessions request."""
    query: str = Field(..., min_length=1, max_length=200)
    search_in_messages: bool = True
    tags: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


# ============================================
# Helper Functions
# ============================================

async def generate_session_title(messages: List[Message], llm_provider=None) -> tuple[str, str]:
    """
    Generate a semantic title and description for a session based on messages.
    Returns (title, description)
    """
    if not messages:
        return "New Chat", ""
    
    # Get first user message for basic title generation
    user_messages = [m for m in messages if m.role == "user"]
    if not user_messages:
        return "New Chat", ""
    
    first_message = user_messages[0].content[:200]
    
    # Simple heuristic-based title generation (no LLM call for speed)
    # Extract key phrases
    title = first_message.split('\n')[0][:50]
    if len(title) < len(first_message.split('\n')[0]):
        title += "..."
    
    # Clean up title
    title = title.strip()
    if not title:
        title = "New Chat"
    
    # Generate description from context
    description = first_message[:150]
    if len(description) < len(first_message):
        description += "..."
    
    return title, description


def get_message_preview(messages: List[Message], max_length: int = 100) -> Optional[str]:
    """Get a preview of the last assistant message."""
    assistant_messages = [m for m in messages if m.role == "assistant"]
    if not assistant_messages:
        return None
    
    last_msg = assistant_messages[-1].content
    if len(last_msg) > max_length:
        return last_msg[:max_length] + "..."
    return last_msg


def parse_tags(session: ChatSession) -> List[str]:
    """Parse tags from session metadata."""
    if session.metadata_json and isinstance(session.metadata_json, dict):
        return session.metadata_json.get("tags", [])
    return []


def is_pinned(session: ChatSession) -> bool:
    """Check if session is pinned."""
    if session.metadata_json and isinstance(session.metadata_json, dict):
        return session.metadata_json.get("is_pinned", False)
    return False


# ============================================
# Endpoints
# ============================================

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: SessionCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> SessionResponse:
    """Create a new chat session."""
    session_repo = SessionRepository(db)
    
    metadata = {
        "tags": request.tags or [],
        "is_pinned": False
    }
    
    session = session_repo.create(
        user_id=current_user.id,
        title=request.title,
        model_name=request.model_name or settings.model_name,
        metadata_json=metadata
    )
    
    logger.info(f"Session created: {session.id} by user {current_user.username}")
    
    return SessionResponse(
        id=session.id,
        title=session.title,
        description=session.description,
        model_name=session.model_name,
        is_active=session.is_active,
        is_archived=session.is_archived,
        is_pinned=is_pinned(session),
        tags=parse_tags(session),
        total_tokens_used=session.total_tokens_used,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0
    )


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_archived: bool = Query(False),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None, max_length=200),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> SessionListResponse:
    """List user's chat sessions with optional filtering."""
    session_repo = SessionRepository(db)
    message_repo = MessageRepository(db)
    
    skip = (page - 1) * page_size
    sessions = session_repo.get_user_sessions(
        user_id=current_user.id,
        include_archived=include_archived,
        skip=skip,
        limit=page_size + 1  # Fetch one extra to check if there are more
    )
    
    has_more = len(sessions) > page_size
    sessions = sessions[:page_size]
    
    # Build response with enriched data
    session_responses = []
    for session in sessions:
        # Filter by tag if specified
        session_tags = parse_tags(session)
        if tag and tag not in session_tags:
            continue
        
        # Filter by search query if specified
        if search:
            search_lower = search.lower()
            if search_lower not in session.title.lower():
                # Check in messages
                messages = message_repo.get_session_messages(session.id, limit=50)
                found = any(search_lower in m.content.lower() for m in messages)
                if not found:
                    continue
        
        messages = message_repo.get_session_messages(session.id, limit=100)
        
        response = SessionResponse(
            id=session.id,
            title=session.title,
            description=session.description,
            model_name=session.model_name,
            is_active=session.is_active,
            is_archived=session.is_archived,
            is_pinned=is_pinned(session),
            tags=session_tags,
            total_tokens_used=session.total_tokens_used,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(messages),
            last_message_preview=get_message_preview(messages)
        )
        session_responses.append(response)
    
    # Sort: pinned first, then by updated_at
    session_responses.sort(key=lambda s: (not s.is_pinned, s.updated_at), reverse=True)
    
    # Get total count
    all_sessions = session_repo.get_user_sessions(
        user_id=current_user.id,
        include_archived=include_archived,
        skip=0,
        limit=10000
    )
    
    return SessionListResponse(
        sessions=session_responses,
        total=len(all_sessions),
        page=page,
        page_size=page_size,
        has_more=has_more
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> SessionDetailResponse:
    """Get a specific session with messages."""
    session_repo = SessionRepository(db)
    message_repo = MessageRepository(db)
    
    session = session_repo.get_user_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    messages = message_repo.get_session_messages(session_id)
    
    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        description=session.description,
        model_name=session.model_name,
        is_active=session.is_active,
        is_archived=session.is_archived,
        is_pinned=is_pinned(session),
        tags=parse_tags(session),
        total_tokens_used=session.total_tokens_used,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(messages),
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                tool_call_id=msg.tool_call_id,
                tool_calls=msg.tool_calls,
                created_at=msg.created_at
            )
            for msg in messages
        ]
    )


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    request: SessionUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> SessionResponse:
    """Update a session."""
    session_repo = SessionRepository(db)
    message_repo = MessageRepository(db)
    
    session = session_repo.get_user_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Build update data
    update_data = {}
    if request.title is not None:
        update_data["title"] = request.title
    if request.description is not None:
        update_data["description"] = request.description
    if request.model_name is not None:
        update_data["model_name"] = request.model_name
    if request.is_archived is not None:
        update_data["is_archived"] = request.is_archived
    
    # Handle metadata updates (tags, is_pinned)
    if request.tags is not None or request.is_pinned is not None:
        current_metadata = session.metadata_json or {}
        if request.tags is not None:
            current_metadata["tags"] = request.tags
        if request.is_pinned is not None:
            current_metadata["is_pinned"] = request.is_pinned
        update_data["metadata_json"] = current_metadata
    
    if update_data:
        session = session_repo.update(session_id, **update_data)
    
    messages = message_repo.get_session_messages(session_id, limit=100)
    
    return SessionResponse(
        id=session.id,
        title=session.title,
        description=session.description,
        model_name=session.model_name,
        is_active=session.is_active,
        is_archived=session.is_archived,
        is_pinned=is_pinned(session),
        tags=parse_tags(session),
        total_tokens_used=session.total_tokens_used,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=len(messages)
    )


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> None:
    """Delete a session and all its messages."""
    session_repo = SessionRepository(db)
    
    session = session_repo.get_user_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session_repo.delete(session_id)
    logger.info(f"Session deleted: {session_id} by user {current_user.username}")


@router.post("/{session_id}/archive", response_model=SessionResponse)
async def archive_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> SessionResponse:
    """Archive a session."""
    session_repo = SessionRepository(db)
    
    session = session_repo.get_user_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session_repo.archive_session(session_id, current_user.id)
    session = session_repo.get_by_id(session_id)
    
    return SessionResponse(
        id=session.id,
        title=session.title,
        description=session.description,
        model_name=session.model_name,
        is_active=session.is_active,
        is_archived=session.is_archived,
        is_pinned=is_pinned(session),
        tags=parse_tags(session),
        total_tokens_used=session.total_tokens_used,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.post("/{session_id}/pin", response_model=SessionResponse)
async def toggle_pin_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> SessionResponse:
    """Toggle pin status of a session."""
    session_repo = SessionRepository(db)
    
    session = session_repo.get_user_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Toggle pin status
    current_metadata = session.metadata_json or {}
    current_pinned = current_metadata.get("is_pinned", False)
    current_metadata["is_pinned"] = not current_pinned
    
    session = session_repo.update(session_id, metadata_json=current_metadata)
    
    return SessionResponse(
        id=session.id,
        title=session.title,
        description=session.description,
        model_name=session.model_name,
        is_active=session.is_active,
        is_archived=session.is_archived,
        is_pinned=not current_pinned,
        tags=parse_tags(session),
        total_tokens_used=session.total_tokens_used,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.post("/{session_id}/generate-title", response_model=GenerateTitleResponse)
async def generate_title(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> GenerateTitleResponse:
    """Auto-generate a semantic title for the session based on conversation."""
    session_repo = SessionRepository(db)
    message_repo = MessageRepository(db)
    
    session = session_repo.get_user_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    messages = message_repo.get_session_messages(session_id, limit=10)
    title, description = await generate_session_title(messages)
    
    # Update session with new title
    session_repo.update(session_id, title=title, description=description)
    
    return GenerateTitleResponse(title=title, description=description)


@router.get("/{session_id}/export", response_model=SessionExportResponse)
async def export_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> SessionExportResponse:
    """Export a session with all messages."""
    session_repo = SessionRepository(db)
    message_repo = MessageRepository(db)
    
    session = session_repo.get_user_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    messages = message_repo.get_session_messages(session_id)
    
    return SessionExportResponse(
        session=SessionResponse(
            id=session.id,
            title=session.title,
            description=session.description,
            model_name=session.model_name,
            is_active=session.is_active,
            is_archived=session.is_archived,
            is_pinned=is_pinned(session),
            tags=parse_tags(session),
            total_tokens_used=session.total_tokens_used,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(messages)
        ),
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                tool_call_id=msg.tool_call_id,
                tool_calls=msg.tool_calls,
                created_at=msg.created_at
            )
            for msg in messages
        ],
        exported_at=datetime.utcnow()
    )


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[MessageResponse]:
    """Get messages for a session."""
    session_repo = SessionRepository(db)
    message_repo = MessageRepository(db)
    
    session = session_repo.get_user_session(session_id, current_user.id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    messages = message_repo.get_session_messages(session_id, skip=skip, limit=limit)
    
    return [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            tool_call_id=msg.tool_call_id,
            tool_calls=msg.tool_calls,
            created_at=msg.created_at
        )
        for msg in messages
    ]
