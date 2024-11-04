# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore
from sqlalchemy import create_engine

from un0.config import settings


@pytest.fixture(scope="class")
def connection():
    eng = create_engine(
        f"{settings.DB_DRIVER}://{settings.DB_NAME}_login@/{settings.DB_NAME}"
    )
    yield eng.connect().execution_options(isolation_level="AUTOCOMMIT")


@pytest.fixture(scope="class")
def create_filter_properties(connection, superuser_id):
    """
    Create the filter properties
    """
    return True
