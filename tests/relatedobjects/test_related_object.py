# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from sqlalchemy import inspect, Integer
from sqlalchemy.dialects.postgresql import VARCHAR

from un0.relatedobjects.models import RelatedObject
from un0.relatedobjects.sql_emitters import RelatedObjectIDFnctnSQL

from tests.conftest import (
    print_indices,
    print_pk_constraint,
    print_foreign_keys,
    print_uq_constraints,
    print_ck_constraints,
    db_column,
)


class TestRelatedObject:
    schema = "un0"

    def test_related_object_model_structure(self):
        assert RelatedObject.__name__ == "RelatedObject"
        assert RelatedObject.__module__ == "un0.relatedobjects.models"
        assert RelatedObject.schema_name == "un0"
        assert RelatedObject.table_name == "related_object"
        assert RelatedObject.table_name_plural == "related_objects"
        assert RelatedObject.verbose_name == "Related Object"
        assert RelatedObject.verbose_name_plural == "Related Objects"
        assert list(RelatedObject.field_definitions.keys()) == ["id", "table_type_id"]
        assert RelatedObject.constraints == []
        assert RelatedObject.indices == []
        assert RelatedObjectIDFnctnSQL in RelatedObject.sql_emitters
        assert RelatedObject.primary_keys == {"id"}

    def test_related_object_indices(self, db_connection):
        """Test the indices on the related_object table in the database."""
        db_inspector = inspect(db_connection)
        # print_indices(db_inspector, "related_object", schema=self.schema)
        assert db_inspector.get_indexes("related_object", schema=self.schema) == [
            {
                "name": "ix_un0_related_object_id",
                "unique": False,
                "column_names": ["id"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
            {
                "name": "ix_un0_related_object_table_type_id",
                "unique": False,
                "column_names": ["table_type_id"],
                "include_columns": [],
                "dialect_options": {"postgresql_include": []},
            },
        ]

    def test_related_object_primary_key(self, db_connection):
        """Test the primary key constraint on the related_object table in the database."""
        db_inspector = inspect(db_connection)
        # print_pk_constraint(db_inspector, "related_object", schema=self.schema)
        assert db_inspector.get_pk_constraint("related_object", schema=self.schema) == {
            "constrained_columns": ["id"],
            "name": "pk_related_object",
            "comment": None,
        }

    def test_related_object_foreign_keys(self, db_connection):
        """Test the foreign keys on the related_object table in the database."""
        db_inspector = inspect(db_connection)
        # print_foreign_keys(db_inspector, "related_object", schema=self.schema)
        assert db_inspector.get_foreign_keys("related_object", schema=self.schema) == [
            {
                "name": "fk_related_object_table_type_id",
                "constrained_columns": ["table_type_id"],
                "referred_schema": "un0",
                "referred_table": "table_type",
                "referred_columns": ["id"],
                "options": {"ondelete": "CASCADE"},
                "comment": None,
            },
        ]

    def test_related_object_unique_constraints(self, db_connection):
        """Test the unique constraints on the related_object table in the database."""
        db_inspector = inspect(db_connection)
        # print_uq_constraints(db_inspector, "related_object", schema=self.schema)
        assert (
            db_inspector.get_unique_constraints("related_object", schema=self.schema)
            == []
        )

    def test_related_object_check_constraints(self, db_connection):
        """Test the check constraints on the related_object table in the database."""
        db_inspector = inspect(db_connection)
        # print_ck_constraints(db_inspector, "related_object", schema=self.schema)
        assert (
            db_inspector.get_check_constraints("related_object", schema=self.schema)
            == []
        )

    def test_related_object_str_method(self):
        """Test the __str__ method on the related_object table in the database."""
        related_object = RelatedObject(id="string", table_type_id=1)
        assert str(related_object) == "1"

    def test_related_object_id_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(db_inspector, "related_object", "id", schema=self.schema)
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), VARCHAR)
        assert column.get("type").length == 26

    def test_related_object_table_type_id_column(self, db_connection):
        db_inspector = inspect(db_connection)
        column = db_column(
            db_inspector, "related_object", "table_type_id", schema=self.schema
        )
        assert column is not None
        assert column.get("nullable") is False
        assert isinstance(column.get("type"), Integer)
