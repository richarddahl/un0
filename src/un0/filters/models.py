# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import textwrap

from datetime import datetime, date, time
from decimal import Decimal

from pydantic import BaseModel, computed_field, ConfigDict
from sqlalchemy import Table, Column

from un0.database.db_tool import TableManager
from un0.utilities import convert_snake_to_capital_word
from un0.filters.enums import (  # type: ignore
    GraphType,
    Include,
    Match,
    Lookup,
    related_lookups,
    numeric_lookups,
    string_lookups,
)
from un0.config import settings
from un0.database.management.db_manager import (
    VertexSqlEmitter,
    EdgeSqlEmitter,
    PropertySqlEmitter,
)
from un0.data.models import UN0Model


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


class FilterFieldModel(UN0Model):
    """A filterfield used to query the database."""

    # name: str <- computed_field
    # accessor: str <- computed_field
    # lookups: list[Lookup] <- computed_field
    # vertex: VertexSqlEmitter | None <- computed_field
    # edge: EdgeSqlEmitter | None <- computed_field
    # props: PropertySqlEmitter | None <- computed_field

    # to_column: Column | None <- computed_field
    table: Table
    column: Column
    graph_type: GraphType

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def name(self) -> str:
        if self.graph_type == GraphType.VERTEX:
            return convert_snake_to_capital_word(self.column.name)
        if self.graph_type == GraphType.EDGE:
            return self.column.name.upper()
        return self.column.name

    @computed_field
    def accessor(self) -> str:
        return self.table.name

    # @computed_field
    # def vertex(self) -> VertexSqlEmitter | None:
    #    if self.graph_type == GraphType.VERTEX:
    #        return VertexSqlSQL(
    #            table=self.table,
    #            column=self.table.primary_key.columns[0],
    #        )
    #    return None
    #
    #    @computed_field
    #    def edge(self) -> EdgeSqlEmitter | None:
    #        if self.graph_type == GraphType.EDGE:
    #            return EdgeSqlSQL(
    #                table=self.table,
    #                from_column=self.from_column,
    #                to_column=self.to_column,
    #            )
    #        return None

    #    @computed_field
    #    def prop(self) -> PropertySqlEmitter | None:
    #        if self.graph_type == GraphType.PROPERTY:
    #            return PropertySqlSQL(table=self.table, column=self.from_column)
    #        return None

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
        return self.prop.accessor

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
            SET ROLE {settings.DB_NAME}_admin;
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
                table_type_id,
                direction
            )
            SELECT
                f.id,
                t.id,
                'FROM'
            FROM un0.table_type t
            JOIN un0.filterfield f
            ON t.db_schema = '{self.table.schema_name}'
            AND t.name = '{self.table.name}'
            AND f.name = '{self.from_column.name}'
            AND f.graph_type = '{self.graph_type.name}'
            ON CONFLICT (filterfield_id, table_type_id, direction) DO NOTHING;
            """
        )
        if self.to_column is not None:
            sql += textwrap.dedent(
                f"""
                -- Associate the FilterField with the TableType
                INSERT INTO un0.filterfield_tabletype (
                    filterfield_id,
                    table_type_id,
                    direction
                )
                SELECT
                    f.id,
                    t.id,
                    'TO'
                FROM un0.table_type t
                JOIN un0.filterfield f
                ON t.db_schema = '{self.table.schema_name}'
                AND t.name = '{self.table.name}'
                AND f.name = '{self.to_column.name}'
                AND f.graph_type = '{self.graph_type.name}'
                ON CONFLICT (filterfield_id, table_type_id, direction) DO NOTHING;
                """
            )
        return sql


class FilterSetSchema(BaseModel):
    # filters = list[FilterFieldSchema] <- computed_field
    table: Table

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def filters(self) -> list[FilterFieldSchema]:
        filters = []
        if self.table.info.get("vertex", True):
            filters.append(
                FilterFieldSchema(
                    table=self.table,
                    column=self.table.primary_key.columns[0],
                    graph_type=GraphType.VERTEX,
                )
            )
        for column in self.table.columns:
            filters.append(
                FilterFieldSchema(
                    table=self.table,
                    column=column,
                    graph_type=GraphType.PROPERTY,
                )
            )
        for fk in self.table.foreign_keys:
            filters.append(
                FilterFieldSchema(
                    table=self.table,
                    to_column=fk.parent,
                    start_vertex=self,
                    end_vertex=VertexSqlSQL(
                        table=fk.column.table,
                        column=fk.parent,
                    ),
                )
            )

        return filters

    def create_sql(self) -> str:
        sql = ""
        for filter in self.filters:
            sql += f"\n{filter.insert_sql()}"
        return sql


'''

class FilterKeySchema(TableManager):
    """ """

    # table: Table <- TableManager

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
            SET ROLE {settings.DB_NAME}_admin;
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


class PathSchema(TableManager):
    """ """

    # table: Table <- TableManager

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
            SET ROLE {settings.DB_NAME}_admin;
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
