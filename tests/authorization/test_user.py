# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from sqlalchemy import inspect, BOOLEAN
from sqlalchemy.dialects.postgresql import TEXT, VARCHAR, TIMESTAMP

from un0.database.fields import CK
from un0.relatedobjects.mixins import InsertRelatedObjectSQL
from un0.authorization.models import User, UserRecordFieldAuditSQL
from un0.database.mixins import SoftDeleteSQL
from un0.database.models import InsertTableTypeSQL

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
        # print(User.field_definitions.keys())
        assert list(User.field_definitions.keys()) == [
            "email",
            "handle",
            "full_name",
            "default_group_id",
            "is_superuser",
            "is_tenant_admin",
            "tenant_id",
            "created_at",
            "owned_by_id",
            "modified_at",
            "modified_by_id",
            "deleted_at",
            "deleted_by_id",
            "id",
            "is_active",
            "is_deleted",
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
            UserRecordFieldAuditSQL,
            InsertTableTypeSQL,
            SoftDeleteSQL,
            InsertRelatedObjectSQL,
        ]:
            assert emitter in User.sql_emitters
        assert User.indices == []
        assert User.primary_keys == {"id"}

        user = User(
            id="string", email="test@example.com", handle="test", full_name="Test User"
        )
        assert str(user) == "test"

    def test_user_primary_key(self, db_connection):
        """Test the primary key constraint on the user table in the database."""
        db_inspector = inspect(db_connection)
        # print_pk_constraint(db_inspector, "user", schema=self.schema)
        assert db_inspector.get_pk_constraint("user", schema=self.schema) == {
            "constrained_columns": ["id"],
            "name": "pk_user",
            "comment": None,
        }

    def test_user_foreign_keys(self, db_connection):
        """Test the foreign keys on the user table in the database."""
        db_inspector = inspect(db_connection)
        # print_foreign_keys(db_inspector, "user", schema=self.schema)
        assert db_inspector.get_foreign_keys("user", schema=self.schema) == [
            {
                "name": "fk_user_default_group_id",
                "constrained_columns": ["default_group_id"],
                "referred_schema": "un0",
                "referred_table": "group",
                "referred_columns": ["id"],
                "options": {"ondelete": "CASCADE"},
                "comment": None,
            },
            {
                "name": "fk_user_deleted_by_id",
                "constrained_columns": ["deleted_by_id"],
                "referred_schema": "un0",
                "referred_table": "user",
                "referred_columns": ["id"],
                "options": {"ondelete": "CASCADE"},
                "comment": None,
            },
            {
                "name": "fk_user_id",
                "constrained_columns": ["id"],
                "referred_schema": "un0",
                "referred_table": "related_object",
                "referred_columns": ["id"],
                "options": {"ondelete": "CASCADE"},
                "comment": None,
            },
            {
                "name": "fk_user_modified_by_id",
                "constrained_columns": ["modified_by_id"],
                "referred_schema": "un0",
                "referred_table": "user",
                "referred_columns": ["id"],
                "options": {"ondelete": "CASCADE"},
                "comment": None,
            },
            {
                "name": "fk_user_owned_by_id",
                "constrained_columns": ["owned_by_id"],
                "referred_schema": "un0",
                "referred_table": "user",
                "referred_columns": ["id"],
                "options": {"ondelete": "CASCADE"},
                "comment": None,
            },
            {
                "name": "fk_user_tenant_id",
                "constrained_columns": ["tenant_id"],
                "referred_schema": "un0",
                "referred_table": "tenant",
                "referred_columns": ["id"],
                "options": {"ondelete": "CASCADE"},
                "comment": None,
            },
        ]

    def test_user_unique_constraints(self, db_connection):
        """Test the unique constraints on the user table in the database."""
        db_inspector = inspect(db_connection)
        # print_uq_constraints(db_inspector, "user", schema=self.schema)
        assert db_inspector.get_unique_constraints("user", schema=self.schema) == []

    def test_user_check_constraints(self, db_connection):
        """Test the check constraints on the user table in the database."""
        db_inspector = inspect(db_connection)
        print_ck_constraints(db_inspector, "user", schema=self.schema)
        assert db_inspector.get_check_constraints("user", schema=self.schema) == [
            {
                "name": "ck_user_ck_user_is_superuser",
                "sqltext": "is_superuser = false AND default_group_id IS NOT NULL OR is_superuser = true AND default_group_id IS NULL AND is_superuser = false AND is_tenant_admin = false OR is_superuser = true AND is_tenant_admin = false OR is_superuser = false AND is_tenant_admin = true",
                "comment": None,
            }
        ]

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

    def test_user_id_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "id", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), VARCHAR)
        assert column.get("type").length == 26

    def test_user_email_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "email", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), TEXT)

    def test_user_handle_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "handle", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), TEXT)

    def test_user_full_name_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "full_name", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), TEXT)

    def test_user_default_group_id_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "default_group_id", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is True
        assert isinstance(column.get("type"), VARCHAR)
        assert column.get("type").length == 26

    def test_user_is_superuser_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "is_superuser", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), BOOLEAN)

    def test_user_is_tenant_admin_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "is_tenant_admin", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), BOOLEAN)

    def test_user_tenant_id_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "tenant_id", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is True
        assert isinstance(column.get("type"), VARCHAR)
        assert column.get("type").length == 26

    def test_user_is_active_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "is_active", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), BOOLEAN)

    def test_user_created_at_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "created_at", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), TIMESTAMP)

    def test_user_owned_by_id_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "owned_by_id", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is True
        assert isinstance(column.get("type"), VARCHAR)
        assert column.get("type").length == 26

    def test_user_modified_at_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "modified_at", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), TIMESTAMP)

    def test_user_modified_by_id_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "modified_by_id", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is True
        assert isinstance(column.get("type"), VARCHAR)
        assert column.get("type").length == 26

    def test_user_is_deleted_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "is_deleted", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), BOOLEAN)

    def test_user_deleted_at_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "deleted_at", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is True
        assert isinstance(column.get("type"), TIMESTAMP)

    def test_user_deleted_by_id_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "deleted_by_id", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is True
        assert isinstance(column.get("type"), VARCHAR)
        assert column.get("type").length == 26

    def test_user_import_id_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "import_id", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is True
        assert isinstance(column.get("type"), TEXT)

    def test_user_import_key_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "user", "import_key", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is True
        assert isinstance(column.get("type"), TEXT)
