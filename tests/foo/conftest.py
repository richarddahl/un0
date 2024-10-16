# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import os
import pytest  # type: ignore

from sqlalchemy.orm import sessionmaker

from tests.foo.models import TestFoo, TestBar, TestBaz
from un0.config import settings as sttngs


@pytest.fixture(scope="class")
def load_data(superuser_id):
    """
    Load the data into the tables
    """
    copy_baz = f"""
        SET 'user_var.id' = "{superuser_id}";
        SET ROLE {sttngs.DB_NAME}_admin;
        COPY un0.testbaz (id, name, description) FROM STDIN WITH CSV HEADER;
        """
    os.system(
        f"psql -U {sttngs.DB_NAME}_login -d {sttngs.DB_NAME} -c '{copy_baz}' < tests/foo/data/baz.csv"
    )
    copy_bar = f"""
        SET 'user_var.id' = "{superuser_id}";
        SET ROLE {sttngs.DB_NAME}_admin;
        COPY un0.testbar(id, name, description, primary_baz_id) FROM STDIN WITH CSV HEADER;
        """
    os.system(
        f"psql -U {sttngs.DB_NAME}_login -d {sttngs.DB_NAME} -c '{copy_bar}' < tests/foo/data/bar.csv"
    )
    copy_foo = f"""
        SET 'user_var.id' = "{superuser_id}";
        SET ROLE {sttngs.DB_NAME}_admin;
        COPY un0.testfoo (id, name, description, bar_id) FROM STDIN WITH CSV HEADER;
        """
    os.system(
        f"psql -U {sttngs.DB_NAME}_login -d {sttngs.DB_NAME} -c '{copy_foo}' < tests/foo/data/foo.csv"
    )
    copy_foobaz = f"""
        SET 'user_var.id' = "{superuser_id}";
        SET ROLE {sttngs.DB_NAME}_admin;
        COPY un0.testfoo_baz FROM STDIN WITH CSV HEADER;
        """
    os.system(
        f"psql -U {sttngs.DB_NAME}_login -d {sttngs.DB_NAME} -c '{copy_foobaz}' < tests/foo/data/foobaz.csv"
    )
    copy_barbaz = f"""
        SET 'user_var.id' = "{superuser_id}";
        SET ROLE {sttngs.DB_NAME}_admin;
        COPY un0.testbar_baz FROM STDIN WITH CSV HEADER;
        """
    os.system(
        f"psql -U {sttngs.DB_NAME}_login -d {sttngs.DB_NAME} -c '{copy_barbaz}' < tests/foo/data/barbaz.csv"
    )


if __name__ == "__main__":
    load_data()
