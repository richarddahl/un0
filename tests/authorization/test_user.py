# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import TEXT, VARCHAR

from un0.database.fields import CK
from un0.database.sql_emitters import (
    EnableDefaultAuditSQL,
    InsertTableTypeSQL,
    SetDefaultActiveSQL,
)
from un0.relatedobjects.sql_emitters import SetRelatedObjectIDSQL
from un0.authorization.models import User
from un0.authorization.sql_emitters import (
    CreatedModifiedFnctnSQL,
    SetDefaultTenantSQL,
    CreatedModifiedTrggrSQL,
    SoftDeleteFnctnSQL,
    SoftDeleteTrggrSQL,
)

from tests.conftest import (
    print_indices,
    print_pk_constraint,
    print_foreign_keys,
    print_uq_constraints,
    print_ck_constraints,
    db_column,
)


class TestUser:
    schema = "un0"

    def test_user_model_structure(self):
        assert User.__name__ == "User"
        assert User.__module__ == "un0.authorization.models"
        assert User.schema_name == "un0"
        assert User.table_name == "user"
        assert User.table_name_plural == "users"
        assert User.verbose_name == "User"
        assert User.verbose_name_plural == "Users"
        assert list(User.field_definitions.keys()) == [
            "email",
            "handle",
            "full_name",
            "default_group_id",
            "is_superuser",
            "is_tenant_admin",
            "tenant_id",
            "id",
            "is_active",
            "created_at",
            "owned_by_id",
            "modified_at",
            "modified_by_id",
            "is_deleted",
            "deleted_at",
            "deleted_by_id",
            "import_id",
            "import_key",
        ]
        assert User.constraints == [
            CK(
                expression="\n(is_superuser = 'false' AND default_group_id IS NOT NULL) OR\n(is_superuser = 'true' AND default_group_id IS NULL) AND\n(is_superuser = 'false' AND is_tenant_admin = 'false') OR\n(is_superuser = 'true' AND is_tenant_admin = 'false') OR\n(is_superuser = 'false' AND is_tenant_admin = 'true')\n",
                name="ck_user_is_superuser",
            )
        ]
        assert User.indices == []
        for emitter in [
            EnableDefaultAuditSQL,
            SetRelatedObjectIDSQL,
            InsertTableTypeSQL,
            SetDefaultActiveSQL,
            CreatedModifiedFnctnSQL,
            CreatedModifiedTrggrSQL,
            SoftDeleteFnctnSQL,
            SoftDeleteTrggrSQL,
            SetDefaultTenantSQL,
        ]:
            assert emitter in User.sql_emitters
        assert User.indices == []
        assert User.primary_keys == {"id"}

    def test_user_indices(self, db_connection):
        """Test the indices on the user table in the database."""
        db_inspector = inspect(db_connection)
        # print_indices(db_inspector, "user", schema=self.schema)
        assert db_inspector.get_indexes("user", schema=self.schema) == [
            {
                "name": "ix_un0_user_default_group_id",
                "unique": False,
                "column_names": ["default_group_id"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
            {
                "name": "ix_un0_user_deleted_by_id",
                "unique": False,
                "column_names": ["deleted_by_id"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
            {
                "name": "ix_un0_user_email",
                "unique": True,
                "column_names": ["email"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
            {
                "name": "ix_un0_user_handle",
                "unique": False,
                "column_names": ["handle"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
            {
                "name": "ix_un0_user_id",
                "unique": True,
                "column_names": ["id"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
            {
                "name": "ix_un0_user_modified_by_id",
                "unique": False,
                "column_names": ["modified_by_id"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
            {
                "name": "ix_un0_user_owned_by_id",
                "unique": False,
                "column_names": ["owned_by_id"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
            {
                "name": "ix_un0_user_tenant_id",
                "unique": False,
                "column_names": ["tenant_id"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
        ]
