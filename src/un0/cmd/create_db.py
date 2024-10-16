# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from un0.db.controller import DBController


if __name__ == "__main__":
    db = DBController()
    db.drop_db()
    db.create_db()
