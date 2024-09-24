# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import pytest
import jwt

import sqlalchemy as sa
import textwrap
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from un0.auth.models import User
from un0.cmd import create_db, drop_db
from un0.config import settings


@pytest.fixture(scope="session")
def engine():
    return sa.create_engine(settings.DB_URL)


@pytest.fixture(scope="session")
def session(engine):
    return Session(engine)


@pytest.fixture(scope="session")
def async_engine():
    return create_async_engine(settings.DB_URL)


@pytest.fixture(scope="session")
def async_session(async_engine):
    return sessionmaker(bind=async_engine, class_=AsyncSession)


@pytest.fixture(scope="session")
def valid_jwt_token(session, email: str | None = None):
    """Returns a JWT token for use in tests."""
    if email is None:
        email = settings.SUPERUSER_EMAIL
        email = "richard@dahl.us"
    expiration = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=settings.TOKEN_EXPIRE_MINUTES
    )
    token_payload = {
        "sub": email,
        "exp": expiration,
    }
    print(token_payload)
    token = jwt.encode(token_payload, settings.TOKEN_SECRET, settings.TOKEN_ALGORITHM)
    return token


@pytest.fixture(scope="session")
def invalid_jwt_token(session, email: str | None = None):
    """Returns a JWT token for use in tests."""
    if email is None:
        email = settings.SUPERUSER_EMAIL
    expiration = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        minutes=settings.TOKEN_EXPIRE_MINUTES
    )
    token_payload = {
        "sub": email,
        "exp": expiration,
    }
    token = jwt.encode(token_payload, settings.TOKEN_SECRET, settings.TOKEN_ALGORITHM)
    return token


@pytest.fixture(scope="session")
def valid_user(session, valid_jwt_token, email: str | None = None):
    """
    TODO: This fixture should be refactored to use async_session.
    """

    if email is None:
        email = settings.SUPERUSER_EMAIL

    with session as _session:
        token_result = _session.execute(
            sa.text(
                f"SELECT * FROM un0.verify_jwt_and_set_session_variables('{valid_jwt_token}'::TEXT);"
            )
        )
        if token_result.scalars().first() is False:
            return None

        _session.execute(sa.text(f"SET ROLE {settings.DB_NAME}_reader"))
        q = sa.sql.select(User).where(User.email == f"{email}")
        result = _session.execute(q)
        admin_user = result.scalars().first()
        return admin_user


@pytest.fixture(scope="session")
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


@pytest.fixture
def test_compare_with_now(db_connection):
    """Test the compare_with_now SQL function."""
    python_timestamp = datetime.datetime.now() - datetime.timedelta(days=1)
    query = textwrap.dedent(
        """
        SELECT un0.compare_with_now(:python_timestamp) AS is_past;
    """
    )
    result = db_connection.execute(
        sa.text(query), {"python_timestamp": python_timestamp}
    )
    is_past = result.scalar()
    assert is_past is True, "The timestamp should be in the past compared to NOW()"
