# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore
from sqlalchemy import create_engine

from un0.fltr.models import FilterField
from un0.config import settings as sttngs


@pytest.fixture(scope="session")
def db_name():
    return "un0_test_fltr"


@pytest.fixture(scope="class")
def connection(db_name):
    eng = create_engine(f"{sttngs.DB_DRIVER}://{db_name}_login@/{db_name}")
    yield eng.connect().execution_options(isolation_level="AUTOCOMMIT")


@pytest.fixture(scope="class")
def create_filter_properties(db_name, connection, superuser_id):
    """
    Create the filter properties
    """
    # create_fields(connection, db_name, superuser_id)
    return True
