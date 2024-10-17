# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from un0.db.models import Un0Base
from un0.auth.tables import User


class UserModel(
    Un0Base,
    module_name=__name__,
    db_table_name="un0.user",
    db_table=User,
):
    pass
