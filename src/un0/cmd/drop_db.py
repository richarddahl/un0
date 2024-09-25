# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import io
import sys

import sqlalchemy as sa

from un0.cmd.sql import (  # type: ignore
    drop_database,
    drop_roles,
)

from un0.config import settings


def drop(db_name: str = settings.DB_NAME) -> None:
    """
    Delete the database and its asociated roles.
    """
    # Connect to the postgres database as the postgres user

    # Redirect the stdout stream to a StringIO object when running tests
    # to prevent the print statements from being displayed in the test output.
    if settings.ENV == "test":
        output_stream = io.StringIO()
        sys.stdout = output_stream

    eng = sa.create_engine("postgresql+psycopg://postgres@/postgres", echo=False)
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print(
            f"\nDropping the db: {settings.DB_NAME} and all the roles for the application\n"
        )
        # Drop the Database
        conn.execute(sa.text(drop_database(db_name=db_name)))
        # Drop the roles
        conn.execute(sa.text(drop_roles(db_name=db_name)))
        conn.close()
        print(f"Database dropped: {db_name} \n")
    eng.dispose()

    # Reset the stdout stream
    if settings.ENV == "test":
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    drop_database()
