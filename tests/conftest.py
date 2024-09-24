# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import pytest
import json

import sqlalchemy as sa
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
def jwt_token(session, email: str | None = None):
    """Returns a JWT token for use in tests."""
    if email is None:
        email = settings.SUPERUSER_EMAIL
    expiration = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
        # - datetime.timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES * 100)
    )
    token_payload = {
        "sub": email,
        "exp": expiration.timestamp(),
    }
    token_str = json.dumps(token_payload)
    print(token_str)
    with session as _session:
        result = _session.execute(
            sa.text(
                f"SELECT * FROM un0.sign('{token_str}', '{settings.TOKEN_SECRET}', '{settings.TOKEN_ALGORITHM}');"
            )
        )
        token = result.scalars().first()
        return token


@pytest.fixture(scope="session")
def admin_user(session, jwt_token):
    """Returns the admin user created in create_db.create_db.
    This fixture is used in tests to verify that the admin user is created correctly
    and for creating new objects.
    TODO: This fixture should be refactored to use async_session.
    """

    with session as _session:
        token = _session.execute(
            sa.text(
                f"SELECT * FROM un0.verify_jwt_and_set_session_variables('{jwt_token}'::TEXT);"
            )
        )
        _session.execute(sa.text(f"SET ROLE {settings.DB_NAME}_reader"))
        q = sa.sql.select(User).where(User.email == f"{settings.SUPERUSER_EMAIL}")
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
