from __future__ import annotations

import textwrap
import pytest

from sqlalchemy import inspect, text, insert, update, Column  # type: ignore

from un0.database.base import metadata
from un0.authorization.enums import TenantType
from un0.config import settings  # type: ignore

'''

class TestDBStructure:
    def test_db_schema_list(self, superuser_id, db_connection):
        db_inspector = inspect(db_connection)
        assert "ag_catalog" in db_inspector.get_schema_names()
        assert "audit" in db_inspector.get_schema_names()
        assert "graph" in db_inspector.get_schema_names()
        assert "public" in db_inspector.get_schema_names()
        assert "un0" in db_inspector.get_schema_names()
        assert settings.DB_SCHEMA in db_inspector.get_schema_names()

    def test_ag_catalog_tables(self, db_connection):
        db_inspector = inspect(db_connection)
        reflected_table_names = db_inspector.get_table_names(schema="ag_catalog")

        for table_name in ["ag_graph", "ag_label"]:
            assert table_name in reflected_table_names

    def test_audit_tables(self, db_connection):
        db_inspector = inspect(db_connection)
        reflected_table_names = db_inspector.get_table_names(schema="audit")

        for table_name in ["record_version"]:
            assert table_name in reflected_table_names

    def test_graph_tables(self, db_connection):
        db_inspector = inspect(db_connection)
        reflected_table_names = db_inspector.get_table_names(schema="graph")

        for table_name in ["_ag_label_edge", "_ag_label_vertex"]:
            assert table_name in reflected_table_names

    def test_public_tables(self, db_connection):
        db_inspector = inspect(db_connection)
        reflected_table_names = db_inspector.get_table_names(schema="public")

        assert reflected_table_names == []

    def test_un0_tables(self, db_connection):
        db_inspector = inspect(db_connection)
        reflected_table_names = db_inspector.get_table_names(schema="un0")

        for table_name in [
            "group",
            "related_object",
            "role",
            "role_table__operation",
            "table_operation",
            "table_type",
            "tenant",
            "token_secret",
            "user",
            "user_group_role",
        ]:
            assert table_name in reflected_table_names

    def test_un0_functions(self, db_connection):
        for function_tuple in [
            ("generate_ulid", None),
            ("permissible_groups", ["table_name", "operation"]),
            ("group_validate_group_insert", None),
            ("verify", ["token", "secret", "algorithm", "header", "payload", "valid"]),
            ("group_validate_group_insert", None),
            ("insert_related_object", None),
            ("set_owner_and_modified", None),
            ("set_token_secret", None),
            ("validate_delete", None),
        ]:
            fnct = db_connection.execute(
                text(
                    f"SELECT oid, proargnames FROM pg_proc WHERE proname = '{function_tuple[0]}';"
                )
            )
            f = fnct.fetchone()
            assert f[0] is not None
            assert f[1] == function_tuple[1]

    def test_un0_types(self, db_connection):
        for enum_tuple in [
            ("sqloperation", ["INSERT", "SELECT", "UPDATE", "DELETE", "TRUNCATE"]),
            ("tenanttype", ["INDIVIDUAL", "BUSINESS", "CORPORATE", "ENTERPRISE"]),
        ]:
            fnct = db_connection.execute(
                text(
                    textwrap.dedent(
                        f"""SELECT oid, enumlabel FROM pg_enum WHERE enumtypid = (
                    SELECT oid FROM pg_type WHERE typname = '{enum_tuple[0]}'
                );"""
                    )
                )
            )
            f = fnct.fetchall()
            assert len(f) == len(enum_tuple[1])
            for i, label in enumerate(enum_tuple[1]):
                assert f[i][1] == label

'''
