# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from sqlalchemy import create_engine

from un0.db import un0.meta_data
from un0.config import settings
# from un0.fltr.filter_creator import FilterFieldCreator


def create_filters():
    """ """
    # Connect to the postgres database as the postgres user
    eng = create_engine("postgresql+psycopg://postgres@/postgres", echo=False)
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        print("Creating filters...")
        conn.close()
    eng.dispose()


if __name__ == "__main__":
    create_filters()
