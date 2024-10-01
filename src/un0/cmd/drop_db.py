# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import io
import sys

from sqlalchemy import create_engine, text

from un0.cmd.sql import (  # type: ignore
    drop_database,
    drop_roles,
)

from un0.config import settings as sttngs


def drop(db_name: str = sttngs.DB_NAME) -> None:
    """
    Delete the database and its asociated roles.
    """
    # Connect to the postgres database as the postgres user

    # Redirect the stdout stream to a StringIO object when running tests
    # to prevent the print statements from being displayed in the test output.
    if sttngs.ENV == "test":
        output_stream = io.StringIO()
        sys.stdout = output_stream

    eng = create_engine("postgresql+psycopg://postgres@/postgres", echo=False)
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print(f"\nDropping the db: {db_name} and all the roles for the application\n")
        # Drop the Database
        conn.execute(text(drop_database(db_name)))
        # Drop the roles
        conn.execute(text(drop_roles(db_name)))
        conn.close()
        print(f"Database dropped: {db_name} \n")
    eng.dispose()

    # Reset the stdout stream
    if sttngs.ENV == "test":
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    drop(db_name=sttngs.DB_NAME)
