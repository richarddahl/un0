# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import pytest
import jwt

from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from un0.cmd import create_db, drop_db
from un0.config import settings
from un0.auth.models import User


SUPERUSER_SESSION_CONFIGURATION_STATEMENTS = f"""
SELECT SET_CONFIG('s_var.user_email', '{settings.SUPERUSER_EMAIL}', true);
SELECT SET_CONFIG('s_var.is_superuser', 'true', true);
SELECT SET_CONFIG('s_var.is_customer_admin', 'false', true);
SELECT SET_CONFIG('s_var.customer_id', '', true);
"""

SET_ROLE_ADMIN_STATEMENT = f"SET ROLE {settings.DB_NAME}_admin;"
SET_ROLE_READER_STATEMENT = f"SET ROLE {settings.DB_NAME}_reader;"
SET_ROLE_WRITER_STATEMENT = f"SET ROLE {settings.DB_NAME}_writer;"


# Not marked as a fixture as need to call it with different parameters for testing
def encode_token(
    email: str = settings.SUPERUSER_EMAIL,  # Email for sub
    has_sub: bool = True,  # Has subject
    has_exp: bool = True,  # Has expiration
    is_expired: bool = False,  # Expired token
    inv_sec: bool = False,  # Invalid secret
):
    """Returns a JWT token for use in tests."""
    token_payload: dict[str, Any] = {}
    if has_exp and not is_expired:
        token_payload["exp"] = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    elif has_exp and is_expired:
        token_payload["exp"] = datetime.datetime.now(
            datetime.timezone.utc
        ) - datetime.timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)
    if has_sub:
        token_payload["sub"] = email

    if inv_sec:
        return jwt.encode(token_payload, "FAKE SECRET", settings.TOKEN_ALGORITHM)
    return jwt.encode(token_payload, settings.TOKEN_SECRET, settings.TOKEN_ALGORITHM)


@pytest.fixture
async def admin_user(async_session):
    token = encode_token()
    async with async_session() as session:
        token_result = await session.execute(
            sa.text(f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);")
        )
        assert token_result.scalars().first() is True
        q = sa.sql.select(User).where(User.email == settings.SUPERUSER_EMAIL)
        result = await session.execute(q)
        return result.scalars().first()


@pytest.fixture(scope="module")
def engine():
    return sa.create_engine(settings.DB_URL)


@pytest.fixture(scope="module")
def session(engine):
    return Session(engine)


@pytest.fixture(scope="module")
def async_engine():
    return create_async_engine(settings.DB_URL)


@pytest.fixture(
    scope="module",
)
def async_session(async_engine):
    return sessionmaker(bind=async_engine, class_=AsyncSession)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    drop_db.drop_database()
    # Create database
    create_db.create_database()
    yield
    # Delete the database after tests
    # drop_db.drop_database()


@pytest.fixture
def db_connection(engine):
    """Returns an sqlalchemy session, and after the test tears down everything properly."""
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()
    yield connection

    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()
