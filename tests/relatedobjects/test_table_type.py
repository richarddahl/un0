# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from sqlalchemy import inspect, Integer
from sqlalchemy.dialects.postgresql import TEXT, VARCHAR

from un0.database.fields import UQ
from un0.relatedobjects.models import TableType
from un0.authorization.sql_emitters import InsertTableOperationFnctnTrggrSQL

from tests.conftest import (
    print_indices,
    print_pk_constraint,
    print_foreign_keys,
    print_uq_constraints,
    print_ck_constraints,
    db_column,
)


class TestTableType:
    schema = "un0"

    def test_table_type_model_structure(self):
        """
        Test the structure of the TableType Model.
        The constraints, indices, and field_definitions are tested in other methods.
        """
        assert TableType.__name__ == "TableType"
        assert TableType.__module__ == "un0.relatedobjects.models"
        assert TableType.schema_name == "un0"
        assert TableType.table_name == "table_type"
        assert TableType.table_name_plural == "table_types"
        assert TableType.verbose_name == "Table Type"
        assert TableType.verbose_name_plural == "Table Types"
        assert list(TableType.field_definitions.keys()) == ["id", "db_schema", "name"]
        assert TableType.constraints == [
            UQ(columns=["db_schema", "name"], name="uq_tabletype_db_schema_name")
        ]
        assert TableType.indices == []
        assert InsertTableOperationFnctnTrggrSQL in TableType.sql_emitters
        assert TableType.primary_keys == {"id"}

        table_type = TableType(db_schema="un0", name="table")
        assert str(table_type) == "un0.table"

    def test_table_type_indices(self, db_connection):
        """Test the indices on the table_type table in the database."""
        db_inspector = inspect(db_connection)
        # print_indices(db_inspector, "table_type", schema=self.schema)
        assert db_inspector.get_indexes("table_type", schema=self.schema) == [
            {
                "name": "ix_un0_table_type_db_schema",
                "unique": False,
                "column_names": ["db_schema"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
            {
                "name": "ix_un0_table_type_id",
                "unique": False,
                "column_names": ["id"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
            {
                "name": "ix_un0_table_type_name",
                "unique": False,
                "column_names": ["name"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
            {
                "name": "uq_tabletype_db_schema_name",
                "unique": True,
                "column_names": ["db_schema", "name"],
                "duplicates_constraint": "uq_tabletype_db_schema_name",
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
        ]

    def test_table_type_primary_key(self, db_connection):
        db_inspector = inspect(db_connection)
        # print_pk_constraint(db_inspector, "table_type", schema=self.schema)
        assert db_inspector.get_pk_constraint("table_type", schema=self.schema) == {
            "constrained_columns": ["id"],
            "name": "pk_table_type",
            "comment": None,
        }

    def test_table_type_foreign_keys(self, db_connection):
        db_inspector = inspect(db_connection)
        # print_foreign_keys(db_inspector, "table_type", schema=self.schema)
        assert db_inspector.get_foreign_keys("table_type", schema=self.schema) == []

    def test_table_type_unique_constraints(self, db_connection):
        db_inspector = inspect(db_connection)
        # print_uq_constraints(db_inspector, "table_type", schema=self.schema)
        assert db_inspector.get_unique_constraints(
            "table_type", schema=self.schema
        ) == [
            {
                "column_names": ["db_schema", "name"],
                "name": "uq_tabletype_db_schema_name",
                "comment": None,
            }
        ]

    def test_table_type_check_constraints(self, db_connection):
        db_inspector = inspect(db_connection)
        # print_ck_constraints(db_inspector, "table_type", schema=self.schema)
        assert (
            db_inspector.get_check_constraints("table_type", schema=self.schema) == []
        )

    def test_table_type_id_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "table_type", "id", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), Integer)

    def test_table_type_db_schema_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "table_type", "db_schema", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), TEXT)

    def test_table_type_name_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "table_type", "name", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), TEXT)
