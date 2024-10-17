# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from un0.db.tools.db_tool import DBTool


if __name__ == "__main__":
    db = DBTool()
    db.drop_db()
    db.create_db()
