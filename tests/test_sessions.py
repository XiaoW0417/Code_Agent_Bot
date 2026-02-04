"""
Tests for session management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.infra.database.models import User, Session as ChatSession


class TestSessionCreate:
    """Tests for session creation."""

    def test_create_session_success(self, client: TestClient, auth_headers: dict):
        """Test successful session creation."""
        response = client.post(
            "/api/v1/sessions",
            json={"title": "My New Chat"},
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "My New Chat"
        assert "id" in data

    def test_create_session_default_title(self, client: TestClient, auth_headers: dict):
        """Test session creation with default title."""
        response = client.post(
            "/api/v1/sessions",
            json={},
            headers=auth_headers
        )
        assert response.status_code == 201
        assert response.json()["title"] == "New Chat"

    def test_create_session_unauthenticated(self, client: TestClient):
        """Test session creation without authentication."""
        response = client.post(
            "/api/v1/sessions",
            json={"title": "Test"}
        )
        assert response.status_code == 403


class TestSessionList:
    """Tests for session listing."""

    def test_list_sessions_empty(self, client: TestClient, auth_headers: dict):
        """Test listing sessions when none exist."""
        response = client.get("/api/v1/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["sessions"] == []
        assert data["total"] == 0

    def test_list_sessions_with_data(
        self, client: TestClient, auth_headers: dict, test_session: ChatSession
    ):
        """Test listing sessions with existing data."""
        response = client.get("/api/v1/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["id"] == test_session.id

    def test_list_sessions_pagination(
        self, client: TestClient, auth_headers: dict, db: Session, test_user: User
    ):
        """Test session list pagination."""
        # Create multiple sessions
        for i in range(5):
            session = ChatSession(
                user_id=test_user.id,
                title=f"Session {i}",
                model_name="gpt-3.5-turbo"
            )
            db.add(session)
        db.commit()

        # Test pagination
        response = client.get(
            "/api/v1/sessions?page=1&page_size=2",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 2
        assert data["total"] == 5


class TestSessionGet:
    """Tests for getting a specific session."""

    def test_get_session_success(
        self, client: TestClient, auth_headers: dict, test_session: ChatSession
    ):
        """Test getting a specific session."""
        response = client.get(
            f"/api/v1/sessions/{test_session.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_session.id
        assert data["title"] == test_session.title

    def test_get_session_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting nonexistent session."""
        response = client.get(
            "/api/v1/sessions/nonexistent-id",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_get_session_other_user(
        self, client: TestClient, db: Session, auth_headers: dict
    ):
        """Test getting another user's session."""
        # Create another user and their session
        other_user = User(
            username="otheruser",
            email="other@example.com",
            hashed_password="hashed",
            is_active=True
        )
        db.add(other_user)
        db.commit()
        
        other_session = ChatSession(
            user_id=other_user.id,
            title="Other's Session",
            model_name="gpt-3.5-turbo"
        )
        db.add(other_session)
        db.commit()

        # Try to access it
        response = client.get(
            f"/api/v1/sessions/{other_session.id}",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestSessionUpdate:
    """Tests for session updates."""

    def test_update_session_title(
        self, client: TestClient, auth_headers: dict, test_session: ChatSession
    ):
        """Test updating session title."""
        response = client.patch(
            f"/api/v1/sessions/{test_session.id}",
            json={"title": "Updated Title"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"


class TestSessionDelete:
    """Tests for session deletion."""

    def test_delete_session_success(
        self, client: TestClient, auth_headers: dict, test_session: ChatSession
    ):
        """Test successful session deletion."""
        response = client.delete(
            f"/api/v1/sessions/{test_session.id}",
            headers=auth_headers
        )
        assert response.status_code == 204

        # Verify it's gone
        response = client.get(
            f"/api/v1/sessions/{test_session.id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_delete_session_not_found(self, client: TestClient, auth_headers: dict):
        """Test deleting nonexistent session."""
        response = client.delete(
            "/api/v1/sessions/nonexistent-id",
            headers=auth_headers
        )
        assert response.status_code == 404
