# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import pytest  # type: ignore
import jwt

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import ProgrammingError

from un0.auth.tables import User
from un0.config import settings as sttngs
from un0.db.base import Base

from tests.conftest import mock_rls_vars


class TestFoo:
    pass
    '''
    def test_foo(self, load_data):
        table = Base.metadata.tables["un0.testfoo"]
        graph_table = FieldSetSchema(table=table)
        """
        print(graph_table.create_insert_sql())
        if graph_table.vertex:
            print(
                "VERTEX: "
                + graph_table.vertex.label
                + ": "
                + graph_table.vertex.data_type
            )
            if graph_table.vertex.properties:
                print("VERTEX PROPERTIES")
                for prop in graph_table.vertex.properties:
                    print(prop.accessor + ": " + prop.data_type)
        if graph_table.edges:
            print("EDGES")
            for edge in graph_table.edges:
                print(
                    edge.start_vertex.label
                    + " - "
                    + edge.label
                    + " -> "
                    + edge.end_vertex.label
                )
                if edge.properties:
                    print("EDGE PROPERTIES")
                    for prop in edge.properties:
                        print(prop.accessor, prop.data_type)
        print("")

        table = Base.metadata.tables["un0.testfoo_baz"]
        graph_table = FieldSetSchema(table=table)
        print("EDGES")
        for edge in graph_table.edges:
            print(
                edge.start_vertex.label
                + " - "
                + edge.label
                + " -> "
                + edge.end_vertex.label
            )
            if edge.properties:
                print("EDGE PROPERTIES")
                for prop in edge.properties:
                    print(prop.accessor, prop.data_type)
        print("")
        """

        assert True

    '''
