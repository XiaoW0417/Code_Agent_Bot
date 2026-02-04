"""
Repository pattern implementation for database operations.
"""
import logging
from typing import Optional, List, TypeVar, Generic, Type
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func

from src.infra.database.models import User, Session as ChatSession, Message, APIUsage
from src.infra.database.connection import Base

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""
    
    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model

    def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination."""
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, **kwargs) -> T:
        """Create a new entity."""
        entity = self.model(**kwargs)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update(self, id: str, **kwargs) -> Optional[T]:
        """Update an entity."""
        entity = self.get_by_id(id)
        if entity:
            for key, value in kwargs.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)
            self.db.commit()
            self.db.refresh(entity)
        return entity

    def delete(self, id: str) -> bool:
        """Delete an entity."""
        entity = self.get_by_id(id)
        if entity:
            self.db.delete(entity)
            self.db.commit()
            return True
        return False


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()

    def get_by_username_or_email(self, identifier: str) -> Optional[User]:
        """Get user by username or email."""
        return self.db.query(User).filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

    def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        self.db.query(User).filter(User.id == user_id).update(
            {"last_login_at": datetime.utcnow()}
        )
        self.db.commit()

    def get_active_users_count(self) -> int:
        """Get count of active users."""
        return self.db.query(func.count(User.id)).filter(User.is_active == True).scalar()


class SessionRepository(BaseRepository[ChatSession]):
    """Repository for Chat Session operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, ChatSession)

    def get_user_sessions(
        self, 
        user_id: str, 
        include_archived: bool = False,
        skip: int = 0, 
        limit: int = 50
    ) -> List[ChatSession]:
        """Get all sessions for a user."""
        query = self.db.query(ChatSession).filter(ChatSession.user_id == user_id)
        if not include_archived:
            query = query.filter(ChatSession.is_archived == False)
        return query.order_by(ChatSession.updated_at.desc()).offset(skip).limit(limit).all()

    def get_user_session(self, session_id: str, user_id: str) -> Optional[ChatSession]:
        """Get a specific session for a user (with ownership check)."""
        return self.db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).first()

    def archive_session(self, session_id: str, user_id: str) -> bool:
        """Archive a session."""
        result = self.db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id
        ).update({"is_archived": True})
        self.db.commit()
        return result > 0

    def update_title(self, session_id: str, title: str) -> Optional[ChatSession]:
        """Update session title."""
        return self.update(session_id, title=title)

    def increment_token_usage(self, session_id: str, tokens: int) -> None:
        """Increment token usage for a session."""
        self.db.query(ChatSession).filter(ChatSession.id == session_id).update(
            {"total_tokens_used": ChatSession.total_tokens_used + tokens}
        )
        self.db.commit()


class MessageRepository(BaseRepository[Message]):
    """Repository for Message operations."""
    
    def __init__(self, db: Session):
        super().__init__(db, Message)

    def get_session_messages(
        self, 
        session_id: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Message]:
        """Get all messages for a session."""
        return self.db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at.asc()).offset(skip).limit(limit).all()

    def get_recent_messages(self, session_id: str, limit: int = 20) -> List[Message]:
        """Get recent messages for context window."""
        return self.db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at.desc()).limit(limit).all()[::-1]

    def add_message(
        self, 
        session_id: str, 
        role: str, 
        content: str,
        tool_call_id: Optional[str] = None,
        tool_calls: Optional[list] = None,
        token_count: Optional[int] = None
    ) -> Message:
        """Add a new message to a session."""
        return self.create(
            session_id=session_id,
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            tool_calls=tool_calls,
            token_count=token_count
        )

    def get_messages_as_dicts(self, session_id: str) -> List[dict]:
        """Get messages formatted for LLM consumption."""
        messages = self.get_session_messages(session_id)
        return [msg.to_dict() for msg in messages]


class APIUsageRepository(BaseRepository[APIUsage]):
    """Repository for API Usage tracking."""
    
    def __init__(self, db: Session):
        super().__init__(db, APIUsage)

    def log_usage(
        self,
        user_id: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        endpoint: str,
        latency_ms: int,
        session_id: Optional[str] = None,
        is_success: bool = True,
        error_code: Optional[str] = None
    ) -> APIUsage:
        """Log API usage."""
        return self.create(
            user_id=user_id,
            session_id=session_id,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            endpoint=endpoint,
            latency_ms=latency_ms,
            is_success=is_success,
            error_code=error_code
        )

    def get_user_usage_stats(self, user_id: str, days: int = 30) -> dict:
        """Get usage statistics for a user."""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        result = self.db.query(
            func.sum(APIUsage.total_tokens).label("total_tokens"),
            func.sum(APIUsage.cost_cents).label("total_cost"),
            func.count(APIUsage.id).label("request_count"),
            func.avg(APIUsage.latency_ms).label("avg_latency")
        ).filter(
            APIUsage.user_id == user_id,
            APIUsage.created_at >= cutoff
        ).first()
        
        return {
            "total_tokens": result.total_tokens or 0,
            "total_cost_cents": result.total_cost or 0,
            "request_count": result.request_count or 0,
            "avg_latency_ms": round(result.avg_latency or 0, 2)
        }
