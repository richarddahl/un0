# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import textwrap

from datetime import datetime, date, time
from decimal import Decimal

from pydantic import BaseModel, computed_field
from sqlalchemy import Table, Column

from un0.schemas import TableSchema
from un0.utilities import convert_snake_to_capital_word
from un0.fltr.enums import (  # type: ignore
    GraphType,
    Include,
    Match,
    Lookup,
    ColumnSecurity,
    related_lookups,
    numeric_lookups,
    string_lookups,
)
from un0.fltr.models import FilterField
from un0.config import settings as sttngs


################
# MATCH SYNTAX #
################
"""
SET search_path TO ag_catalog;
SELECT * FROM cypher('graph', $$
MATCH (s)-[r:IS_OWNED_BY]-(d)
return s, r, d
$$) AS (source agtype, Relationship agtype, Destination agtype);
"""


'''
class FilterSchema(BaseModel):
    """A filter used to query the database."""

    table: Table
    graph_type: GraphType
    label: str
    include: Include
    match: Match
    lookups: list[Lookup]


class FilterFieldSchema(BaseModel):
    """A field used to filter a query."""

    table: Table
    from_column: Column
    to_column: Column | None = None
    graph_type: GraphType
    vertex: VertexSchema | None = None
    edge: EdgeSchema | None = None
    prop: PropertySchema | None = None
    lookups: list[Lookup] = []
    label: str

    @computed_field
    def vertex(self) -> VertexSchema | None:
        if self.graph_type == GraphType.VERTEX:
            return VertexSchema(table=self.table, column=self.from_column)
        return None

    @computed_field
    def edge(self) -> EdgeSchema | None:
        if self.graph_type == GraphType.EDGE:
            return EdgeSchema(
                table=self.table,
                start_column=self.from_column,
                end_column=self.to_column,
            )
        return None

    @computed_field
    def prop(self) -> PropertySchema | None:
        if self.graph_type == GraphType.PROPERTY:
            return PropertySchema(table=self.table, column=self.from_column)
        return None

    @computed_field
    def lookups(self) -> list[Lookup]:
        if self.prop:
            return self.prop.lookups
        return related_lookups

    @computed_field
    def label(self) -> str:
        if self.vertex:
            return self.vertex.label
        if self.edge:
            return self.edge.label
        return self.prop.name



class FilterFieldSchemaOLD(TableSchema):
    """ """

    # table: Table <- TableSchema

    # vertex: VertexSchema | None <- computed_field
    # edge: EdgeSchema | None <- computed_field
    # prop: PropertySchema | None <- computed_field
    # lookups: list[Lookup] <- computed_field
    # label: str <- computed_field

    from_column: Column
    to_column: Column | None = None
    graph_type: GraphType

    @computed_field
    def vertex(self) -> VertexSchema | None:
        if self.graph_type == GraphType.VERTEX:
            return VertexSchema(table=self.table, column=self.from_column)
        return None

    @computed_field
    def edge(self) -> EdgeSchema | None:
        if self.graph_type == GraphType.EDGE:
            return EdgeSchema(
                table=self.table,
                start_column=self.from_column,
                end_column=self.to_column,
            )
        return None

    @computed_field
    def prop(self) -> PropertySchema | None:
        if self.graph_type == GraphType.PROPERTY:
            return PropertySchema(table=self.table, column=self.from_column)
        return None

    @computed_field
    def lookups(self) -> list[Lookup]:
        if self.prop:
            return self.prop.lookups
        return related_lookups

    @computed_field
    def label(self) -> str:
        if self.vertex:
            return self.vertex.label
        if self.edge:
            return self.edge.label
        return self.prop.name

    def insert_sql(self) -> str:
        sql = ""
        if self.vertex:
            sql += self.vertex.create_sql()
        elif self.edge:
            sql += self.edge.create_label_sql()
        #    sql += self.create_sql_function(
        #        "insert_edges",
        #        self.edge.create_insert_function_and_trigger_sql(),
        #        operation="INSERT",
        #        include_trigger=True,
        #    )
        #    sql += self.create_sql_function(
        #        "update_edges",
        #        self.edge.create_update_function_and_trigger_sql(),
        #        include_trigger=True,
        #    )
        #    sql += self.create_sql_function(
        #        "delete_edges",
        #        self.edge.create_delete_function_and_trigger_sql(),
        #        operation="DELETE",
        #        include_trigger=True,
        #    )
        #    sql += self.create_sql_function(
        #        "truncate_edges",
        #        self.edge.create_truncate_function_and_trigger_sql(),
        #        operation="TRUNCATE",
        #        for_each="STATEMENT",
        #        include_trigger=True,
        #    )
        sql += textwrap.dedent(
            f"""
            SET ROLE {sttngs.DB_NAME}_admin;
            -- Create the FilterField
            INSERT INTO un0.filterfield(
                name,
                accessor,
                graph_type,
                lookups
            )
            VALUES (
                '{self.from_column.name}',
                '{self.label}',
                '{self.graph_type.name}',
                ARRAY{self.lookups}::un0.lookup[]
            )
            ON CONFLICT (accessor) DO NOTHING;

            -- Associate the FilterField with the TableType
            INSERT INTO un0.filterfield_tabletype (
                filterfield_id,
                tabletype_id,
                direction
            )
            SELECT
                f.id,
                t.id,
                'FROM'
            FROM un0.tabletype t
            JOIN un0.filterfield f
            ON t.schema = '{self.table.schema}'
            AND t.name = '{self.table.name}'
            AND f.name = '{self.from_column.name}'
            AND f.graph_type = '{self.graph_type.name}'
            ON CONFLICT (filterfield_id, tabletype_id, direction) DO NOTHING;
            """
        )
        if self.to_column is not None:
            sql += textwrap.dedent(
                f"""
                -- Associate the FilterField with the TableType
                INSERT INTO un0.filterfield_tabletype (
                    filterfield_id,
                    tabletype_id,
                    direction
                )
                SELECT
                    f.id,
                    t.id,
                    'TO'
                FROM un0.tabletype t
                JOIN un0.filterfield f
                ON t.schema = '{self.table.schema}'
                AND t.name = '{self.table.name}'
                AND f.name = '{self.to_column.name}'
                AND f.graph_type = '{self.graph_type.name}'
                ON CONFLICT (filterfield_id, tabletype_id, direction) DO NOTHING;
                """
            )
        return sql


class FilterKeySchema(TableSchema):
    """ """

    # table: Table <- TableSchema

    from_filterfield: FilterFieldSchema
    to_filterfield: FilterFieldSchema
    label: str

    @computed_field
    def start_filter_field(self) -> FilterFieldSchema:
        return self.edge_filter_field.from_column

    @computed_field
    def end_filter_field(self) -> FilterFieldSchema:
        return self.edge_filter_field.to_column

    def insert_sql(self) -> str:
        return textwrap.dedent(
            f"""
            SET ROLE {sttngs.DB_NAME}_admin;
            -- Create the FilterKey
            INSERT INTO un0.filterkey(
                from_filterfield_id,
                to_filterfield_id,
                accessor
            )
            VALUES (
                (SELECT id FROM un0.filterfield
                WHERE accessor = '{self.from_filterfield.label}'),
                (SELECT id FROM un0.filterfield
                WHERE accessor = '{self.to_filterfield.label}'),
                '{self.label}'
            )
            ON CONFLICT (from_filterfield_id, to_filterfield_id, accessor) DO NOTHING;
            """
        )


class PathSchema(TableSchema):
    """ """

    # table: Table <- TableSchema

    # start_filter_field: FilterFieldSchema <- computed_field
    # end_filter_field: FilterFieldSchema <- computed_field
    # children: list["PathSchema"] = [] <- computed_field

    edge_filter_field: FilterFieldSchema
    parent_filter_field: FilterFieldSchema | None = None

    @computed_field
    def start_filter_field(self) -> FilterFieldSchema:
        return self.edge_filter_field.edge.start_vertex.filter_field

    @computed_field
    def end_filter_field(self) -> FilterFieldSchema:
        return self.edge_filter_field.edge.end_vertex.filter_field

    @computed_field
    def children(self) -> list["PathSchema"]:
        children = []
        for child_edge in self.end_filter_field.vertex.edges:
            children.append(
                PathSchema(
                    table=self.table,
                    edge_filter_field=child_edge.filter_field,
                    parent=self,
                )
            )
        return children

    def insert_sql(self) -> str:
        return textwrap.dedent(
            f"""
            SET ROLE {sttngs.DB_NAME}_admin;
            -- Create the Path
            INSERT INTO un0.filterkey(
                start_filter_field_id,
                edge_filter_field_id,
                end_filter_field_id,
                parent_filter_field_id
            )
            VALUES (
                (SELECT id FROM un0.filterfield WHERE accessor = '{self.start_filter_field.label}' AND graph_type = 'VERTEX'),
                (SELECT id FROM un0.filterfield WHERE accessor = '{self.edge_filter_field.label}' AND graph_type = 'EDGE'),
                (SELECT id FROM un0.filterfield WHERE accessor = '{self.end_filter_field.label}' AND graph_type = 'VERTEX'),
            )
            ON CONFLICT (name) DO NOTHING;
            """
        )

'''
