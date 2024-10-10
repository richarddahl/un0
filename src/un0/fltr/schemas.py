# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import textwrap

from datetime import datetime, date, time
from decimal import Decimal

from pydantic import BaseModel, computed_field
from sqlalchemy import Table, Column

from un0.schemas import UnoBaseSchema
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


class PropertySchema(UnoBaseSchema):
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


class VertexSchema(UnoBaseSchema):
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
            props.append(
                PropertySchema(table=self.table, db_name=self.db_name, column=column)
            )
        return props

    # Functions to generate sql statements
    def create_sql(self, edges: list["EdgeSchema"] | None) -> str:
        return textwrap.dedent(
            "\n".join(
                [
                    self.create_label_sql(),
                    self.create_insert_function_and_trigger_sql(edges),
                    self.create_update_function_and_trigger_sql(edges),
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
                IF NOT EXISTS (SELECT 1 FROM ag_catalog.ag_label WHERE name = '{self.label}') THEN
                    PERFORM ag_catalog.create_vlabel('graph', '{self.label}');
                    CREATE INDEX ON graph."{self.label}" (id);
                END IF;
            END $$;
            """
        )

    def create_insert_function_and_trigger_sql(
        self, edges: list["EdgeSchema"] | None
    ) -> str:
        """Creates a new vertex record when a new relational table record is inserted"""
        prop_key_str = ""
        prop_val_str = ""
        edge_str = ""
        if edges:
            edge_str = "\n".join([edge.create_sql() for edge in edges])

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
            self.create_sql_stmt(
                "insert_vertex",
                sql,
                operation="INSERT",
                include_trigger=True,
            )
        )

    def create_update_function_and_trigger_sql(
        self, edges: list["EdgeSchema"] | None
    ) -> str:
        """Updates an existing vertex record when its relational table record is updated"""
        prop_key_str = ""
        prop_val_str = ""
        edge_str = ""
        if edges:
            edge_str = "\n".join([edge.create_sql() for edge in edges])
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
            self.create_sql_stmt(
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
            self.create_sql_stmt(
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
            self.create_sql_stmt(
                "truncate_vertex",
                sql,
                operation="truncate",
                for_each="STATEMENT",
                include_trigger=True,
            )
        )


class EdgeSchema(UnoBaseSchema):
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


class GraphedTableSchema(UnoBaseSchema):
    """
    Edges represent the foreign keys in the table.
    Association tables will not have a vertex, but will have edges.
    Their tables edges will be from each of the foreign keys to each of the other foreign keys.
    Those edges may have properties, i.e. all non-foreign key columns in the table.
    'Normal' tables will have a vertex and generally have edges.
    Their edges will be from the vertex (representing the table itself) to each of the foreign keys.
    """

    # table: Table <- UnoBaseSchema
    # db_name: str <- UnoBaseSchema

    # vertex: VertexSchema | None <- computed_field
    # edges: list[EdgeSchema] | None <- computed_field
    # field_set: list[FilterFieldSchema] | None <- computed_field

    @computed_field
    def vertex(self) -> VertexSchema | None:
        """
        Returns a VertexSchema instance if the column is the primary key of the table, unless
        the table.info dictionary contains a "vertex" key with a value of False.
        Otherwise, it returns None.
        """
        if self.table.info.get("vertex", True) is False:
            return None
        return VertexSchema(
            table=self.table, db_name=self.db_name, column=self.table.columns["id"]
        )

    @computed_field
    def edges(self) -> list[EdgeSchema] | None:
        edges = []
        if self.table.info.get("vertex", True) is False:
            """
            Association table
            Edges are created between each of the foreign keys in the table.
            """
            for fk in self.table.foreign_keys:
                for column in self.table.columns:
                    if fk.parent.name == column.name:
                        continue
                    for _fk in column.foreign_keys:
                        edges.append(
                            EdgeSchema(
                                table=self.table,
                                db_name=self.db_name,
                                start_column=fk.parent,
                                end_column=column,
                            )
                        )
        else:
            """
            Normal table
            Edges are created between the vertex and each of the foreign keys in the table.
           """
            start_column = self.table.columns["id"]
            for column in self.table.columns:
                for fk in column.foreign_keys:
                    if start_column != column:
                        edges.append(
                            EdgeSchema(
                                table=self.table,
                                db_name=self.db_name,
                                start_column=start_column,
                                end_column=column,
                            )
                        )

        return edges

    @computed_field
    def field_set(self) -> list["FilterFieldSchema"] | None:
        field_set = []
        if self.vertex:
            field_set.append(
                FilterFieldSchema(
                    table=self.table,
                    db_name=self.db_name,
                    column=self.table.columns["id"],
                    graph_type=GraphType.VERTEX,
                    vertex=self.vertex,
                    edge=None,
                    prop=None,
                )
            )
            for prop in self.vertex.properties:
                field_set.append(
                    FilterFieldSchema(
                        table=self.table,
                        db_name=self.db_name,
                        column=prop.column,
                        graph_type=GraphType.PROPERTY,
                        prop=prop,
                        vertex=None,
                        edge=None,
                    )
                )
        for edge in self.edges:
            field_set.append(
                FilterFieldSchema(
                    table=self.table,
                    db_name=self.db_name,
                    column=edge.end_column,
                    graph_type=GraphType.EDGE,
                    edge=edge,
                    vertex=None,
                    prop=None,
                )
            )
        return field_set

    def generate_sql(self) -> str:
        sql = ""
        if self.vertex:
            sql += self.vertex.create_sql(self.edges)
        else:
            edge_label_sql = "\n".join([edge.create_label_sql() for edge in self.edges])
            edge_insert_sql = "\n".join(
                [
                    self.create_sql_stmt(
                        "insert_edges",
                        edge.create_insert_function_and_trigger_sql(),
                        operation="INSERT",
                        include_trigger=True,
                    )
                    for edge in self.edges
                ]
            )
            edge_update_sql = "\n".join(
                [
                    self.create_sql_stmt(
                        "update_edges",
                        edge.create_update_function_and_trigger_sql(),
                        include_trigger=True,
                    )
                    for edge in self.edges
                ]
            )
            edge_delete_sql = "\n".join(
                [
                    self.create_sql_stmt(
                        "delete_edges",
                        edge.create_delete_function_and_trigger_sql(),
                        operation="DELETE",
                        include_trigger=True,
                    )
                    for edge in self.edges
                ]
            )
            edge_truncate_sql = "\n".join(
                [
                    self.create_sql_stmt(
                        "truncate_edges",
                        edge.create_truncate_function_and_trigger_sql(),
                        operation="TRUNCATE",
                        for_each="STATEMENT",
                        include_trigger=True,
                    )
                    for edge in self.edges
                ]
            )

            sql += f"{edge_label_sql}\n{edge_insert_sql}\n{edge_update_sql}\n{edge_delete_sql}\n{edge_truncate_sql}"
        sql += "\n".join([field.insert_sql() for field in self.field_set])
        return sql


class FilterFieldSchema(UnoBaseSchema):
    """ """

    # table: Table <- UnoBaseSchema
    # db_name: str <- UnoBaseSchema

    # data_type: str <- computed_field
    # lookups: list[Lookup] <- computed_field
    # label: str <- computed_field

    vertex: VertexSchema | None
    edge: EdgeSchema | None
    prop: PropertySchema | None
    column: Column
    graph_type: GraphType = GraphType.PROPERTY

    @computed_field
    def data_type(self) -> str:
        if self.vertex:
            return GraphType.VERTEX
        if self.edge:
            return GraphType.EDGE
        return GraphType.PROPERTY

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
        return textwrap.dedent(
            f"""
            SET ROLE {self.db_name}_admin;
            -- Create the FilterField
            INSERT INTO un0.filterfield(
                name,
                accessor,
                data_type,
                graph_type,
                lookups
            )
            VALUES (
                '{self.column.name}',
                '{self.label}',
                '{self.data_type}',
                '{self.graph_type.name}',
                ARRAY{self.lookups}::un0.lookup[]
            )
            ON CONFLICT (accessor, graph_type) DO NOTHING;

            -- Associate the FilterField with the TableType
            INSERT INTO un0.filterfield_tabletype (
                filterfield_id,
                tabletype_id
            )
            SELECT
                f.id,
                t.id
            FROM un0.tabletype t
            JOIN un0.filterfield f
            ON t.schema = '{self.table.schema}'
            AND t.name = '{self.table.name}'
            AND f.name = '{self.column.name}'
            AND f.graph_type = '{self.graph_type.name}'
            ON CONFLICT (filterfield_id, tabletype_id) DO NOTHING;
            """
        )

    '''
    def insert_filtervertex_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Create the FilterVertex
            INSERT INTO un0.filtervertex (
                tabletype_id,
                label
            )
            SELECT
                t.id,
                '{self.vertex.label}'
            FROM un0.tabletype t
            WHERE t.schema = '{self.table.schema}'
            AND t.name = '{self.table.name}'
            ON CONFLICT (tabletype_id, label) DO NOTHING;

            -- Associate the FilterField with the FilterVertex
            INSERT INTO un0.filterfield_filtervertex (
                field_id,
                vertex_id
            )
            SELECT
                f.id,
                v.id
            FROM un0.filterfield f
            JOIN un0.filtervertex v
            ON f.field_name = '{self.name}'
            AND v.label = '{self.vertex.label}'
            ON CONFLICT (field_id, vertex_id) DO NOTHING
            """
        )

    def insert_filteredge_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Create the FilterEdge
            INSERT INTO un0.filteredge(
                label
            )
            VALUES('{self.edge.label}')
            ON CONFLICT (label) DO NOTHING;

            -- Associate the FilterField with the FilterVertex
            INSERT INTO un0.filterfield_filteredge(
                field_id,
                edge_id
            )
            SELECT
                f.id,
                e.id
            FROM un0.filterfield f
            JOIN un0.filteredge e
            ON f.field_name = '{self.name}'
            AND e.label = '{self.edge.label}'
            ON CONFLICT (field_id, edge_id) DO NOTHING
            """
        )
    '''
