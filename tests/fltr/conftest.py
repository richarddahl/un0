# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore
from sqlalchemy import create_engine

from un0.config import settings as sttngs


@pytest.fixture(scope="class")
def connection():
    eng = create_engine(
        f"{sttngs.DB_DRIVER}://{sttngs.DB_NAME}_login@/{sttngs.DB_NAME}"
    )
    yield eng.connect().execution_options(isolation_level="AUTOCOMMIT")


@pytest.fixture(scope="class")
def create_filter_properties(connection, superuser_id):
    """
    Create the filter properties
    """
    return True
