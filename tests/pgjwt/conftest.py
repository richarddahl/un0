# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime
import pytest  # type: ignore
import jwt

from typing import Any

import sqlalchemy as sa

from un0.cmd.sql import set_role_writer
from un0.config import settings as sttngs
from un0.auth.models import User


@pytest.fixture
def db_name() -> str:
    return "un0_test_jwt"


@pytest.fixture
def db_url(db_name: str) -> str:
    return f"{sttngs.DB_DRIVER}://{db_name}_login:{sttngs.DB_USER_PW}@{sttngs.DB_HOST}:{sttngs.DB_PORT}/{db_name}"


@pytest.fixture
def session(db_url: str) -> sa.orm.Session:
    return sa.orm.sessionmaker(sa.create_engine(db_url))()


@pytest.fixture
def load_inactive_user(
    session: sa.orm.Session, mock_superuser_session_variables: str, db_name: str
) -> None:
    user = User(
        email="inactive@user.com",
        handle="inactive_user",
        full_name="Inactive User",
        is_active=False,
    )
    with session as session:
        session.execute(sa.text(mock_superuser_session_variables))
        session.execute(sa.text(set_role_writer(db_name=db_name)))
        session.add(user)
        session.commit()


@pytest.fixture
def load_deleted_user(
    session: sa.orm.Session, mock_superuser_session_variables: str, db_name: str
) -> None:
    user = User(
        email="deleted@user.com",
        handle="deleted_user",
        full_name="Deleted User",
        is_deleted=True,
    )
    with session as session:
        session.execute(sa.text(mock_superuser_session_variables))
        session.execute(sa.text(set_role_writer(db_name=db_name)))
        session.add(user)
        session.commit()


# Not marked as a fixture as need to call it with different parameters for testing
def encode_test_token(
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
