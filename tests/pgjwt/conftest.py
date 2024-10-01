# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from tests.conftest import get_mock_user_vars

from un0.cmd import create_db, drop_db
from un0.auth.models import User
from un0.config import settings as sttngs


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
def superuser_id(db_name):
    """Creates the database and returns the superuser id."""
    print(f"Creating database {db_name}")
    drop_db.drop(db_name)
    superuser_id = create_db.create(db_name)
    yield superuser_id


@pytest.fixture(scope="session")
def session(engine, superuser_id, create_test_functions):
    session = sessionmaker(bind=engine)
    yield session()
    engine.dispose()
