# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import io
import sys

from sqlalchemy import create_engine, text

from un0.cmd.sql import (  # type: ignore
    DROP_DATABASE,
    DROP_ROLES,
)

from un0.config import settings as sttngs


def drop() -> None:
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
        print(
            f"\nDropping the db: {sttngs.DB_NAME} and all the roles for the application\n"
        )
        # Drop the Database
        conn.execute(text(DROP_DATABASE))
        # Drop the roles
        conn.execute(text(DROP_ROLES))
        conn.close()
        print(f"Database dropped: {sttngs.DB_NAME} \n")
    eng.dispose()

    # Reset the stdout stream
    if sttngs.ENV == "test":
        sys.stdout = sys.__stdout__


if __name__ == "__main__":
    drop()
