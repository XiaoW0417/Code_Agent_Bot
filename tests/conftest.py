"""
Pytest configuration and fixtures.
"""
import os
import pytest
from typing import Generator
from unittest.mock import MagicMock, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["OPENAI_API_KEY"] = "test-api-key"

from src.infra.database.connection import Base, get_db
from src.infra.database.models import User, Session as ChatSession, Message
from src.infra.auth.password import hash_password
from src.infra.auth.jwt import create_access_token
from src.api.app import create_app


# Test database engine
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    """Override database dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create a test client with database override."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hash_password("TestPassword123"),
        display_name="Test User",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """Create an access token for the test user."""
    return create_access_token(test_user.id, test_user.username)


@pytest.fixture
def auth_headers(test_user_token: str) -> dict:
    """Create authorization headers."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def test_session(db: Session, test_user: User) -> ChatSession:
    """Create a test chat session."""
    session = ChatSession(
        user_id=test_user.id,
        title="Test Session",
        model_name="gpt-3.5-turbo"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def mock_llm() -> MagicMock:
    """Create a mock LLM provider."""
    mock = MagicMock()
    mock.chat_complete = AsyncMock(return_value=MagicMock(content="Test response"))
    mock.chat_stream = AsyncMock(return_value=iter(["Test ", "response"]))
    return mock
