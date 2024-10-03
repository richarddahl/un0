# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from sqlalchemy import text, create_engine

from un0.auth.sql import create_superuser
from un0.config import settings as sttngs


def create(
    db_name: str = sttngs.DB_NAME,
    email: str = sttngs.SUPERUSER_EMAIL,
    handle: str = sttngs.SUPERUSER_HANDLE,
    full_name: str = sttngs.SUPERUSER_FULL_NAME,
) -> str:
    """ """
    eng = create_engine(f"{sttngs.DB_DRIVER}://{db_name}_login@/{db_name}")
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"SET ROLE {db_name}_admin"))
        conn.execute(text("ALTER TABLE un0.user DISABLE ROW LEVEL SECURITY;"))
        superuser = conn.execute(text(create_superuser(email, handle, full_name)))
        superuser_id = superuser.scalar()
        conn.execute(text(f"SET ROLE {db_name}_admin"))
        conn.execute(text("ALTER TABLE un0.user ENABLE ROW LEVEL SECURITY;"))
        conn.execute(text("ALTER TABLE un0.user FORCE ROW LEVEL SECURITY;"))
    eng.dispose()

    return superuser_id


if __name__ == "__main__":
    create(
        email=sttngs.SUPERUSER_EMAIL,
        handle=sttngs.SUPERUSER_HANDLE,
        full_name=sttngs.SUPERUSER_FULL_NAME,
        is_superuser=True,
    )
