# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from un0.database.management.db_manager import DBManager


if __name__ == "__main__":
    db = DBManager()
    db.drop_db()
    db.create_db()
