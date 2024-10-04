# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import sys
import os
import pytest  # type: ignore

from tests.foo.models import TestFoo, TestBar, TestBaz
from un0.config import settings as sttngs


@pytest.fixture(scope="session")
def db_name():
    return "un0_test_foo"


@pytest.fixture(scope="class")
def load_data(db_name):
    """
    Load the data into the tables
    """
    copy_baz = (
        f"SET ROLE {db_name}_admin; COPY un0.test_baz FROM STDIN WITH CSV HEADER;"
    )
    os.system(
        f"psql -U {db_name}_login -d {db_name} -c '{copy_baz}' < tests/foo/data/baz.csv"
    )
    copy_baz = (
        f"SET ROLE {db_name}_admin; COPY un0.test_bar FROM STDIN WITH CSV HEADER;"
    )
    os.system(
        f"psql -U {db_name}_login -d {db_name} -c '{copy_baz}' < tests/foo/data/bar.csv"
    )
    copy_baz = (
        f"SET ROLE {db_name}_admin; COPY un0.test_foo FROM STDIN WITH CSV HEADER;"
    )
    os.system(
        f"psql -U {db_name}_login -d {db_name} -c '{copy_baz}' < tests/foo/data/foo.csv"
    )
