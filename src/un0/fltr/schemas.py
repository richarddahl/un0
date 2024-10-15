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


class PropertySchema(TableSchema):
    """
    PropertySchema is a model representing an Apache AGE graph property.

    Attributes:
        column (Column): The column associated with the graph property.
        model_config (dict): Configuration dictionary allowing arbitrary types.

    Computed Properties:
        name() -> str:
            Returns the name of the column.
        data_type() -> str:
            Returns the SQL type of the column, formatted for use in a SQL query.
    """

    column: Column

    # name: str <- computed_field
    # data_type: str <- computed_field
    # lookups: Lookup <- computed_field

    model_config = {"arbitrary_types_allowed": True}

    @computed_field
    def name(self) -> str:
        return self.column.name

    @computed_field
    def data_type(self) -> str:
        """Get the column type for a given column"""
        return f"quote_nullable(NEW.{self.name}::{self.column.type})"
        # return f"quote_nullable(NEW.{self.column.name}::TEXT)"

    @computed_field
    def lookups(self) -> Lookup:
        if self.column.type.python_type in [
            int,
            float,
            Decimal,
            datetime,
            date,
            time,
        ]:
            return numeric_lookups
        return string_lookups


class VertexSchema(TableSchema):
    """An Apache AGE vertex

    Vertices represent the 'Normal' tables in the database.
    Association tables will not have a vertex, but will have edges.
    """

    table: Table
    column: Column
    lookups: list[Lookup] = related_lookups

    # label: str <- computed_field
    # data_type: str <- computed_field
    # properties: list[PropertySchema] | None <- computed_field
    # edges: list[EdgeSchema] | None <- computed_field

    model_config = {"arbitrary_types_allowed": True}

    @computed_field
    def label(self) -> str:
        return convert_snake_to_capital_word(self.table.name)

    @computed_field
    def data_type(self) -> str:
        """Get the column type for a given column"""
        return f"quote_nullable(NEW.{self.column.name}::{self.column.type})"

    @computed_field
    def properties(self) -> list["PropertySchema"] | None:
        props = []
        for column in self.table.columns:
            props.append(PropertySchema(table=self.table, column=column))
        return props

    @computed_field
    def edges(self) -> list["EdgeSchema"] | None:
        edges = []
        for fk in self.table.foreign_keys:
            for column in self.table.columns:
                if fk.parent.name == column.name:
                    continue
                for _fk in column.foreign_keys:
                    edges.append(
                        EdgeSchema(
                            table=self.table,
                            start_column=fk.parent,
                            end_column=column,
                        )
                    )
        return edges

    # Functions to generate sql statements
    def create_sql(self) -> str:
        return textwrap.dedent(
            "\n".join(
                [
                    self.create_label_sql(),
                    self.create_insert_function_and_trigger_sql(),
                    self.create_update_function_and_trigger_sql(),
                    self.create_delete_function_and_trigger_sql(),
                    self.create_truncate_function_and_trigger_sql(),
                ]
            )
        )

    def create_label_sql(self):
        return textwrap.dedent(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM ag_catalog.ag_label
                WHERE name = '{self.label}') THEN
                    PERFORM ag_catalog.create_vlabel('graph', '{self.label}');
                    CREATE INDEX ON graph."{self.label}" (id);
                END IF;
            END $$;
            """
        )

    def create_insert_function_and_trigger_sql(self) -> str:
        """Creates a new vertex record when a new relational table record is inserted"""
        prop_key_str = ""
        prop_val_str = ""
        edge_str = ""
        if self.edges:
            edge_str = "\n".join(
                [edge.create_insert_function_and_trigger_sql() for edge in self.edges]
            )

        if self.properties:
            prop_key_str = ", ".join(f"{prop.name}: %s" for prop in self.properties)
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        sql = textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                CREATE (v:{self.label} {{{prop_key_str}}})
            $$) AS (a agtype);'{prop_val_str});
            {edge_str}
            RETURN NEW;
            """
        )
        return textwrap.dedent(
            self.create_sql_function(
                "insert_vertex",
                sql,
                operation="INSERT",
                include_trigger=True,
            )
        )

    def create_update_function_and_trigger_sql(self) -> str:
        """Updates an existing vertex record when its relational table record is updated"""
        prop_key_str = ""
        prop_val_str = ""
        edge_str = ""
        if self.edges:
            edge_str = "\n".join(
                [edge.create_update_function_and_trigger_sql() for edge in self.edges]
            )
        if self.properties:
            prop_key_str = "SET " + ", ".join(
                f"v.{prop.name} = %s" for prop in self.properties
            )
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        sql = textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.label} {{id: %s}})
                {prop_key_str}
            $$) AS (a agtype);', quote_nullable(NEW.id){prop_val_str});
            {edge_str}
            RETURN NEW;
            """
        )
        return textwrap.dedent(
            self.create_sql_function(
                "update_vertex",
                sql,
                include_trigger=True,
            )
        )

    def create_delete_function_and_trigger_sql(self) -> str:
        """Deleted an existing vertex record when its relational table record is deleted"""
        sql = textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.label} {{id: %s}})
                DETACH DELETE v
            $$) AS (a agtype);', quote_nullable(OLD.id));
            RETURN OLD;
            """
        )
        return textwrap.dedent(
            self.create_sql_function(
                "delete_vertex",
                sql,
                operation="DELETE",
                include_trigger=True,
            )
        )

    def create_truncate_function_and_trigger_sql(self) -> str:
        """Deletes all corresponding vertices for a relation table when the table is truncated"""
        sql = textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.label})
                DETACH DELETE v
            $$) AS (a agtype);');
            RETURN OLD;
            """
        )
        return textwrap.dedent(
            self.create_sql_function(
                "truncate_vertex",
                sql,
                operation="truncate",
                for_each="STATEMENT",
                include_trigger=True,
            )
        )


class EdgeSchema(TableSchema):
    """
    EdgeSchema is a class representing an edge in an Apache AGE graph.
    It inherits from GraphBase and includes attributes for the edge label, start vertex, and end vertex.
    The class provides methods to create edge labels, compute properties, and generate SQL statements for
    creating edges between vertices.

    Attributes:
        label (str): The label of the edge.
        start_vertex (VertexSchema): The starting vertex of the edge.
        end_vertex (VertexSchema): The ending vertex of the edge.

    Methods:
        create_elabel(self):
            Generates SQL statements to create an edge label and an index on the edge.

        properties(self) -> list["PropertySchema"]:
            Computes and returns a list of properties for the edge based on the table's columns.

        create_edge_sql_statement(self) -> str:
            Creates and returns the Cypher SQL statements to create edges between vertices, including properties if they exist.
    """

    table: Table
    start_column: Column
    end_column: Column
    lookups: list[Lookup] = related_lookups

    # label: str <- computed_field
    # start_vertex: VertexSchema <- computed_field
    # end_vertex: VertexSchema <- computed_field
    # properties: list[PropertySchema] <- computed_field

    model_config = {"arbitrary_types_allowed": True}

    @computed_field
    def label(self) -> str:
        return self.end_column.info.get("edge")

    @computed_field
    def start_vertex(self) -> VertexSchema:
        return VertexSchema(table=self.start_column.table, column=self.start_column)

    @computed_field
    def end_vertex(self) -> VertexSchema:
        return VertexSchema(table=self.end_column.table, column=self.end_column)

    @computed_field
    def properties(self) -> list["PropertySchema"]:
        """
        Retrieves a list of graph properties for the current table.

        Returns:
            list[PropertySchema]: A list of PropertySchema objects representing the properties of the graph.
        """
        props = []
        for column in self.table.columns:
            if not column.foreign_keys:
                props.append(PropertySchema(table=self.table, column=column))
        return props

    # Functions to generate sql statements

    def create_sql(self) -> str:
        """
        Generates SQL statements to create a table in the graph.

        This method generates SQL statements to create a table in a graph database.
        The table is created based on the vertex information of the table.
        If the table is a normal table, the vertex is created with an index on the 'id' column.
        If the table is an association table, the edges are created between the foreign keys.

        Returns:
            str: The SQL statement to create the table in the graph.
        """
        return textwrap.dedent(
            "\n".join(
                [
                    self.create_label_sql(),
                    self.create_insert_function_and_trigger_sql(),
                    self.create_update_function_and_trigger_sql(),
                    self.create_delete_function_and_trigger_sql(),
                    self.create_truncate_function_and_trigger_sql(),
                ]
            )
        )

    def create_label_sql(self) -> str:
        """
        Generates an SQL query string to create an edge label and an index for a graph.

        Returns:
            str: A formatted SQL query string that creates an edge label in the 'graph' schema
             and an index on the 'start_id' and 'end_id' columns of the created label.
        """
        return textwrap.dedent(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM ag_catalog.ag_label WHERE name = '{self.label}') THEN
                    PERFORM ag_catalog.create_elabel('graph', '{self.label}');
                    CREATE INDEX ON graph."{self.label}" (start_id, end_id);
                END IF;
            END $$;
            """
        )

    def create_insert_function_and_trigger_sql(self) -> str:
        """ """
        prop_key_str = ""
        prop_val_str = ""
        if self.properties:
            prop_key_str = ", ".join(f"{prop.name}: %s" for prop in self.properties)
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        return textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                CREATE (v)-[e:{self.label} {{{prop_key_str}}}] ->(w)
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type}{prop_val_str});
            """
        )

    def create_update_function_and_trigger_sql(self) -> str:
        """
        Generates an SQL query string to update an edge in a graph database.

        The method constructs a SQL query that:
        1. Matches the start and end vertices based on their labels and IDs.
        2. Deletes the existing edge between the matched vertices.
        3. Creates a new edge with the same label and updated properties.

        Returns:
            str: The formatted SQL query string.
        """
        prop_key_str = ""
        prop_val_str = ""
        if self.properties:
            prop_key_str = "SET " + ", ".join(
                f"v.{prop.name} = %s" for prop in self.properties
            )
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        return textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                MATCH (v)-[o:{self.label}] ->(w)
                DELETE o
                CREATE (v)-[e:{self.label}] ->(w)
                {prop_key_str}
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type}{prop_val_str});
            """
        )

    def create_delete_function_and_trigger_sql(self) -> str:
        """
        Generates an SQL query string to delete an edge in a graph database.

        The generated SQL query uses the `cypher` function to match and delete an edge
        between two vertices identified by their labels and IDs. The edge to be deleted
        is specified by the label of the edge.

        Returns:
            str: The SQL query string to delete the specified edge.
        """

        return textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                MATCH (v)-[o:{self.label}] ->(w)
                DELETE o
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type});
            """
        )

    def create_truncate_function_and_trigger_sql(self) -> str:
        """
        Generates an SQL query string to truncate (delete) an edge in a graph database.

        The generated SQL query uses the `cypher` function to match and delete an edge
        between two vertices based on their labels and IDs.

        Returns:
            str: The SQL query string to truncate the specified edge.
        """
        return textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                MATCH (v)-[o:{self.label}] ->(w)
                DELETE o
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type});
            """
        )


class FilteredTableSchema(TableSchema):
    """
    Edges represent the foreign keys in the table.
    Association tables will not have a vertex, but will have edges.
    Their tables edges will be from each of the foreign keys to each of the other foreign keys.
    Those edges may have properties, i.e. all non-foreign key columns in the table.
    'Normal' tables will have a vertex and generally have edges.
    Their edges will be from the vertex (representing the table itself) to each of the foreign keys.
    """

    # table: Table <- TableSchema

    # field_set: list[FilterFieldSchema] | None <- computed_field

    @computed_field
    def field_set(self) -> list["FilterFieldSchema"] | None:
        field_set = []
        if self.table.info.get("vertex", True):
            field_set.append(
                FilterFieldSchema(
                    table=self.table,
                    from_column=self.table.columns["id"],
                    graph_type=GraphType.VERTEX,
                )
            )
        for column in self.table.columns:
            field_set.append(
                FilterFieldSchema(
                    table=self.table,
                    from_column=column,
                    graph_type=GraphType.PROPERTY,
                )
            )
        for fk in self.table.foreign_keys:
            for column in self.table.columns:
                if fk.parent.name == column.name:
                    continue
                for _fk in column.foreign_keys:
                    field_set.append(
                        FilterFieldSchema(
                            table=self.table,
                            from_column=fk.parent,
                            to_column=column,
                            graph_type=GraphType.EDGE,
                        )
                    )
        return field_set

    def generate_sql(self) -> str:
        return "\n".join(
            [textwrap.dedent(field.insert_sql()) for field in self.field_set]
        )


class FilterFieldSchema(TableSchema):
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
