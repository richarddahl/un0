# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sqlalchemy as sa

from un0.cmd.sql import (  # type: ignore
    DROP_DATABASE,
    DROP_ROLES,
)

from un0.config import settings


def drop_database():
    """
    Delete the database and its asociated roles.
    """
    # Connect to the postgres database as the postgres user
    eng = sa.create_engine("postgresql+psycopg://postgres@/postgres", echo=False)
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print(
            f"\nDropping the db: {settings.DB_NAME} and all the roles for the application\n"
        )
        # Drop the Database
        conn.execute(sa.text(DROP_DATABASE))
        # Drop the roles
        conn.execute(sa.text(DROP_ROLES))
        conn.close()
        print(f"Database dropped: {settings.DB_NAME} \n")
    eng.dispose()


if __name__ == "__main__":
    drop_database()
