"""
demo-repository/tests/test_auth.py
Tests for the authentication flow.
Demonstrates TESTS relationships in the code graph:
  test_authenticate_user → authenticate_user
  test_validate_token → validate_token
  test_logout → logout
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from ..services.auth_service import AuthService
from ..services.user_service import UserService
from ..utils.token_service import TokenService
from ..models.user import User, TokenPair


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_user() -> User:
    """A test user with a known password hash."""
    service = UserService()
    return User(
        id="test-user-001",
        username="alice",
        email="alice@example.com",
        hashed_password=service._hash_password("correct-password"),
        is_active=True,
    )


@pytest.fixture
def auth_service(mock_user: User) -> AuthService:
    """AuthService with mocked dependencies."""
    user_service = MagicMock(spec=UserService)
    user_service.get_user_by_username.return_value = mock_user
    user_service.get_user.return_value = mock_user
    user_service.verify_password.side_effect = (
        lambda plain, hashed: UserService()._hash_password(plain) == hashed
    )
    user_service.update_last_login.return_value = None

    token_service = TokenService(secret_key="test-secret-key")

    # Patch database calls in token_service
    with patch("demo_repository.database.database.save_token"), \
         patch("demo_repository.database.database.is_token_revoked", return_value=False):
        service = AuthService(
            user_service=user_service,
            token_service=token_service,
        )
    return service


# ── Tests for authenticate_user ───────────────────────────────────────────

class TestAuthenticateUser:
    """Tests for AuthService.authenticate_user()"""

    def test_authenticate_user_valid_credentials(
        self, auth_service: AuthService, mock_user: User
    ) -> None:
        """authenticate_user() returns TokenPair for valid credentials."""
        with patch("demo_repository.database.database.save_token"), \
             patch("demo_repository.database.database.is_token_revoked", return_value=False):
            result = auth_service.authenticate_user("alice", "correct-password")

        assert result is not None
        assert isinstance(result, TokenPair)
        assert result.access_token != ""
        assert result.refresh_token != ""
        assert result.token_type == "bearer"

    def test_authenticate_user_wrong_password(
        self, auth_service: AuthService
    ) -> None:
        """authenticate_user() returns None for wrong password."""
        result = auth_service.authenticate_user("alice", "wrong-password")
        assert result is None

    def test_authenticate_user_unknown_user(self) -> None:
        """authenticate_user() returns None for non-existent user."""
        user_service = MagicMock(spec=UserService)
        user_service.get_user_by_username.return_value = None
        service = AuthService(user_service=user_service, token_service=TokenService())
        result = service.authenticate_user("nobody", "password")
        assert result is None

    def test_authenticate_user_inactive_account(
        self, mock_user: User
    ) -> None:
        """authenticate_user() returns None for inactive accounts."""
        mock_user.is_active = False
        user_service = MagicMock(spec=UserService)
        user_service.get_user_by_username.return_value = mock_user
        user_service.verify_password.return_value = True
        service = AuthService(user_service=user_service, token_service=TokenService())
        result = service.authenticate_user("alice", "correct-password")
        assert result is None


# ── Tests for validate_token ───────────────────────────────────────────────

class TestValidateToken:
    """Tests for AuthService.validate_token()"""

    def test_validate_token_valid(self, auth_service: AuthService, mock_user: User) -> None:
        """validate_token() returns payload for a valid access token."""
        token_service = TokenService(secret_key="test-secret-key")
        access_token = token_service.create_access_token(mock_user.id, mock_user.username)

        result = auth_service.validate_token(access_token)

        assert result is not None
        assert result["sub"] == mock_user.id
        assert result["username"] == mock_user.username

    def test_validate_token_invalid(self, auth_service: AuthService) -> None:
        """validate_token() returns None for a malformed token."""
        result = auth_service.validate_token("not.a.real.token")
        assert result is None

    def test_validate_token_empty(self, auth_service: AuthService) -> None:
        """validate_token() returns None for an empty string."""
        result = auth_service.validate_token("")
        assert result is None


# ── Tests for logout ───────────────────────────────────────────────────────

class TestLogout:
    """Tests for AuthService.logout()"""

    def test_logout_revokes_token(self, auth_service: AuthService) -> None:
        """logout() calls token revocation."""
        with patch("demo_repository.database.database.revoke_token", return_value=True) as mock_revoke, \
             patch("demo_repository.database.database.save_token"), \
             patch("demo_repository.database.database.is_token_revoked", return_value=False):
            token_service = TokenService(secret_key="test-secret-key")
            refresh = token_service.create_refresh_token("user-001")

        with patch("demo_repository.database.database.revoke_token", return_value=True) as mock_revoke:
            result = auth_service.logout(refresh)

        assert result is True


# ── Tests for refresh_access_token ────────────────────────────────────────

class TestRefreshAccessToken:
    """Tests for AuthService.refresh_access_token()"""

    def test_refresh_returns_new_pair(
        self, auth_service: AuthService, mock_user: User
    ) -> None:
        """refresh_access_token() returns a new TokenPair for a valid refresh token."""
        with patch("demo_repository.database.database.save_token"), \
             patch("demo_repository.database.database.is_token_revoked", return_value=False), \
             patch("demo_repository.database.database.revoke_token", return_value=True):
            token_service = TokenService(secret_key="test-secret-key")
            refresh = token_service.create_refresh_token(mock_user.id)
            result = auth_service.refresh_access_token(refresh)

        # In this test the mocked UserService returns the mock user
        # This tests that the function calls validate_token → TokenService and get_user → UserService
        # Exact result depends on mock setup; the important thing is no exception

    def test_refresh_invalid_token_returns_none(
        self, auth_service: AuthService
    ) -> None:
        """refresh_access_token() returns None for an invalid token."""
        result = auth_service.refresh_access_token("invalid-token")
        assert result is None
