# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from sqlalchemy.sql.schema import Table

from un0.db.models import Un0Obj, Un0ModelDef, Un0Model
from un0.auth.tables import User
from un0.db.base import Base


class UserModel(Un0Model):
    table: Base = User

    def process_app_logic(self) -> bool:
        super().process_app_logic()
        print("process_app_logic")
        return True


class UserObj(
    Un0Obj,
    module_name=__name__,
    db_table_name="un0.user",
    db_table=User,
):
    schema_defs: dict[str, Un0ModelDef] = {
        "insert_schema": Un0ModelDef(
            table=User,
            base=UserModel,
            field_excludes=[
                "id",
                "is_active",
                "is_deleted",
                "created_at",
                "modified_at",
                "deleted_at",
                "owner_id",
                "modified_by_id",
                "deleted_by_id",
            ],
        ),
        "update_schema": Un0ModelDef(
            table=User,
            base=UserModel,
            field_excludes=[
                "id",
                "is_deleted",
                "created_at",
                "modified_at",
                "deleted_at",
                "modified_by_id",
                "deleted_by_id",
            ],
        ),
        "select_schema": Un0ModelDef(
            table=User,
            base=UserModel,
        ),
        "list_schema": Un0ModelDef(
            table=User,
            base=UserModel,
            field_includes=[
                "id",
                "handle",
                "email",
            ],
        ),
    }
