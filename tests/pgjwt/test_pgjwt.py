# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import pytest  # type: ignore
import jwt

from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import ProgrammingError

from un0.config import settings as sttngs


class TestJWT:
    # Not marked as a fixture as need to call it with different parameters for testing
    @classmethod
    def encode_test_token(
        cls,
        email: str = sttngs.SUPERUSER_EMAIL,  # Email for sub
        has_sub: bool = True,  # Has subject
        has_exp: bool = True,  # Has expiration
        is_expired: bool = False,  # Expired token
        invalid_secret: bool = False,  # Invalid secret
    ) -> str:
        """Returns a JWT token for use in tests."""
        token_payload: dict[str, Any] = {}
        if has_exp and not is_expired:
            token_payload["exp"] = datetime.datetime.now(
                datetime.timezone.utc
            ) + datetime.timedelta(minutes=sttngs.TOKEN_EXPIRE_MINUTES)
        elif has_exp and is_expired:
            token_payload["exp"] = datetime.datetime.now(
                datetime.timezone.utc
            ) - datetime.timedelta(minutes=sttngs.TOKEN_EXPIRE_MINUTES)

        if has_sub:
            token_payload["sub"] = email

        if invalid_secret:
            return jwt.encode(token_payload, "FAKE SECRET", sttngs.TOKEN_ALGORITHM)
        return jwt.encode(token_payload, sttngs.TOKEN_SECRET, sttngs.TOKEN_ALGORITHM)

    def test_valid_jwt(self, session):
        """Tests that a valid JWT token can be verified and the session variables set."""
        print("THERE")
        token = self.encode_test_token()
        with session as session:
            result = session.execute(func.un0.set_user_vars(token))
            assert result.scalars().first() is True

            result = session.execute(func.un0.test_list_user_vars())
            session_variables = result.scalars().first()
            assert session_variables.get("email") == sttngs.SUPERUSER_EMAIL
            assert session_variables.get("id") != ""
            assert session_variables.get("is_superuser") == "true"
            assert session_variables.get("is_tenant_admin") == "false"
            assert session_variables.get("tenant_id") == ""


'''
    def test_expired_jwt(self, session):
        """Tests that an expired JWT token cannot be authorized."""
        token = self.encode_test_token(is_expired=True)
        with session as session:
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute(func.un0.set_user_vars(token))
            assert "invalid token" in str(excinfo.value)

    def test_invalid_secret_jwt(self, session):
        """Tests that a JWT token with an invalid secret cannot be authorized."""
        token = self.encode_test_token(invalid_secret=True)
        with session as session:
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute(func.un0.set_user_vars(token))
            assert "invalid token" in str(excinfo.value)

    def test_invalid_sub_jwt(self, session):
        """Tests that a JWT token with an invalid sub cannot be authorized."""
        token = self.encode_test_token(email="richard@dahl.us")
        with session as session:
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute(func.un0.set_user_vars(token))
            assert "user not found" in str(excinfo.value)

    def test_no_sub_jwt(self, session):
        """Tests that a JWT token without a sub cannot be authorized."""
        token = self.encode_test_token(has_sub=False)
        with session as session:
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute(func.un0.set_user_vars(token))
            assert "no sub in token" in str(excinfo.value)

    def test_no_exp_jwt(self, session):
        """Tests that a JWT token without an expiration cannot be authorized."""
        token = self.encode_test_token(has_exp=False)
        with session as session:
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute(func.un0.set_user_vars(token))
            assert "no exp in token" in str(excinfo.value)

    def test_inactive_user_jwt(self, session, load_inactive_user):
        """Tests that an inactive user cannot be authorized."""
        token = self.encode_test_token(email="inactive@user.com")
        with session as session:
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute(func.un0.set_user_vars(token))
            assert "user is not active" in str(excinfo.value)


    def test_deleted_user_jwt(self, session, load_deleted_user):
        """Tests that a deleted user cannot be authorized."""
        token = self.encode_test_token(email="deleted@user.com")
        with session as session:
            with pytest.raises(ProgrammingError) as excinfo:
                session.execute(func.un0.set_user_vars(token))
            assert "user was deleted" in str(excinfo.value)
'''
