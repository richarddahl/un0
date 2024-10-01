# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore

from sqlalchemy import create_engine, func, select, delete
from sqlalchemy.orm import sessionmaker, Session

from tests.conftest import get_mock_user_vars

from un0.cmd import create_db, drop_db
from un0.config import settings as sttngs
from un0.auth.models import User


@pytest.fixture(scope="session")
def db_name():
    return "un0_test_jwt"


@pytest.fixture(scope="session")
def db_url(db_name):
    return f"{sttngs.DB_DRIVER}://{db_name}_login:{sttngs.DB_USER_PW}@{sttngs.DB_HOST}:{sttngs.DB_PORT}/{db_name}"


@pytest.fixture(scope="session")
def engine(db_url):
    yield create_engine(db_url)


@pytest.fixture(scope="session")
def connection(engine):
    yield engine.connect()
    engine.dispose()


@pytest.fixture(scope="session")
def db(db_name):
    drop_db.drop(db_name)
    create_db.create(db_name)


@pytest.fixture(scope="session")
def session(db, engine, connection):
    session = sessionmaker(bind=connection, expire_on_commit=False)
    yield session()
    connection.close()
    engine.dispose()


@pytest.fixture(scope="function")
def load_inactive_user(session: Session) -> None:
    user = User(
        email="inactive@user.com",
        handle="inactive_user",
        full_name="Inactive User",
        is_active=False,
    )
    with session.begin():
        session.execute(func.un0.test_set_mock_user_vars(*get_mock_user_vars()))
        session.execute(func.un0.set_role("writer"))
        session.add(user)
        session.commit()


@pytest.fixture(scope="function")
def load_deleted_user(session: Session) -> None:
    user = User(
        email="deleted@user.com",
        handle="deleted_user",
        full_name="Deleted User",
        is_deleted=True,
    )
    with session.begin():
        session.execute(func.un0.test_set_mock_user_vars(*get_mock_user_vars()))
        session.execute(func.un0.set_role("writer"))
        session.add(user)
        session.commit()


@pytest.fixture(scope="session")
def test_list_user_vars():
    """Returns the function name for the test_list_user_vars function."""
    return "SELECT * FROM un0.test_list_user_vars();"
