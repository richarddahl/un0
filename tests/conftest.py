# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from un0.cmd import create_db, drop_db
from un0.config import settings


@pytest.fixture(scope="session")
def engine():
    return create_engine(settings.DB_URL)


@pytest.fixture(scope="session")
def async_engine():
    return create_async_engine(settings.DB_URL)


@pytest.fixture(scope="session")
def async_session(async_engine):
    return sessionmaker(bind=async_engine, class_=AsyncSession)


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
