# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import textwrap

from pydantic import BaseModel, computed_field
from sqlalchemy import Table, Column

from un0.utilities import convert_snake_to_capital_word
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


class GraphBase(BaseModel):
    """
    GraphBase is a base class for Apache AGE graph objects, inheriting from BaseModel.
    It provides methods and attributes to manage and interact with graph-related database tables.

    Attributes:
        table (Table): The table associated with the graph object.
        db_name (str): The name of the database, defaulting to the value from settings (sttngs.DB_NAME).
        model_config (dict): Configuration dictionary allowing arbitrary types.

    Methods:
        table_schema() -> str:
            A computed property that returns the schema of the associated table.

        table_name() -> str:
            A computed property that returns the name of the associated table.

        create_sql_function(
            include_trigger: bool = False
            Generates a SQL function and optionally a trigger for the associated table.

            Parameters:
                function_name (str): The name of the function to create.
                execution_string (str): The SQL execution string to be included in the function body.
                operation (str, optional): The operation type for the trigger (default is "UPDATE").
                for_each (str, optional): Specifies whether the trigger is for each row or statement (default is "ROW").
                include_trigger (bool, optional): Whether to include a trigger creation statement (default is False).

            Returns:
                str: The generated SQL function and optionally the trigger as a string.
    """

    table: Table
    db_name: str = sttngs.DB_NAME

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @computed_field
    def table_schema(self) -> str:
        return self.table.schema

    @computed_field
    def table_name(self) -> str:
        return self.table.name

    def create_sql_stmt(
        self,
        function_name: str,
        execution_string: str,
        operation: str = "UPDATE",
        for_each: str = "ROW",
        include_trigger: bool = False,
    ) -> str:
        func_string = textwrap.dedent(
            f"""
            CREATE OR REPLACE FUNCTION {self.table_schema}.{self.table_name}_{function_name}()
                RETURNS TRIGGER
                LANGUAGE plpgsql
                VOLATILE
            AS $BODY$
            BEGIN
                SET ROLE {self.db_name}_admin;
                {execution_string}
            END;
            $BODY$;
            """
        )
        trigger_string = textwrap.dedent(
            f"""
            CREATE OR REPLACE TRIGGER {self.table_name}_{function_name}_trigger
                AFTER {operation}
                ON {self.table_schema}.{self.table_name}
                FOR EACH {for_each}
                EXECUTE FUNCTION {self.table_schema}.{self.table_name}_{function_name}();
            """
        )
        sql_str = f"{func_string}\n{trigger_string}" if include_trigger else func_string
        return textwrap.dedent(sql_str)


class GraphProperty(BaseModel):
    """
    GraphProperty is a model representing an Apache AGE graph property.

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

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @computed_field
    def name(self) -> str:
        return self.column.name

    @computed_field
    def data_type(self) -> str:
        """Get the column type for a given column"""
        return f"quote_nullable(NEW.{self.column.name}::{self.column.type})"


class GraphVertex(GraphBase):
    """An Apache AGE vertex

    Vertices represent the 'Normal' tables in the database.
    Association tables will not have a vertex, but will have edges.
    """

    @computed_field
    def label(self) -> str:
        return convert_snake_to_capital_word(self.table_name)

    @computed_field
    def data_type(self) -> str:
        """Get the column type for a given column"""
        column = self.table.columns["id"]
        return f"quote_nullable(NEW.{column.name}::{column.type})"

    @computed_field
    def properties(self) -> list["GraphProperty"]:
        props = []
        for column in self.table.columns:
            if column.foreign_keys:
                continue
            else:
                props.append(GraphProperty(column=column))
        return props

    def create_vlabel_sql(self):
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


class GraphEdge(GraphBase):
    """
    GraphEdge is a class representing an edge in an Apache AGE graph.
    It inherits from GraphBase and includes attributes for the edge label, start vertex, and end vertex.
    The class provides methods to create edge labels, compute properties, and generate SQL statements for
    creating edges between vertices.

    Attributes:
        label (str): The label of the edge.
        start_vertex (GraphVertex): The starting vertex of the edge.
        end_vertex (GraphVertex): The ending vertex of the edge.

    Methods:
        create_elabel(self):
            Generates SQL statements to create an edge label and an index on the edge.

        properties(self) -> list["GraphProperty"]:
            Computes and returns a list of properties for the edge based on the table's columns.

        create_edge_sql_statement(self) -> str:
            Creates and returns the Cypher SQL statements to create edges between vertices, including properties if they exist.
    """

    label: str
    start_vertex: GraphVertex
    end_vertex: GraphVertex

    @computed_field
    def properties(self) -> list["GraphProperty"]:
        """
        Retrieves a list of graph properties for the current table.

        Returns:
            list[GraphProperty]: A list of GraphProperty objects representing the properties of the graph.
        """
        props = []
        if self.table.info.get("vertex", True) is False:
            for column in self.table.columns:
                if column.foreign_keys:
                    continue
                else:
                    props.append(GraphProperty(column=column))
        return props

    def edge_sql(self) -> str:
        """
        Creates the Cypher statements to create edges between vertices.

        This method generates SQL statements to create edges in a graph database.
        The edges are created between vertices based on the foreign keys of the table.
        If the table is an association table, the edges may have additional properties
        derived from non-foreign key columns in the table.

        Returns:
            str: The SQL statement to create the edges.
        """
        property_keys_str = ""
        property_values_str = ""
        if self.properties:
            property_keys_str = "SET " + ", ".join(
                [prop.name for prop in self.properties if prop.name != "id"]
            )
            property_values_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties if prop.name != "id"]
            )
        return textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                CREATE (v)-[e:{self.label} {{{property_keys_str}}}] ->(w)
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type}{property_values_str});
            """
        )

    def create_elabel_sql(self) -> str:
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
                    CREATE INDEX ON graph."{self.label}"(start_id, end_id);
                END IF;
            END $$;
            """
        )


class TableGraph(GraphBase):
    """
    TableGraph is a class that represents an Apache AGE representation of a SQLAlchemy database table.

    Edges represent the foreign keys in the table.
    Association tables will not have a vertex, but will have edges.
    Their tables edges will be from each of the foreign keys to each of the other foreign keys.
    Those edges may have properties, i.e. all non-foreign key columns in the table.
    'Normal' tables will have a vertex and generally have edges.
    Their edges will be from the vertex (representing the table itself) to each of the foreign keys.
    """

    @computed_field
    def vertex(self) -> GraphVertex | None:
        """
        Returns a GraphVertex instance if the table has vertex information.

        This method checks if the table's info dictionary contains a "vertex" key
        with a value of True. If so, it returns a new GraphVertex instance
        initialized with the table. Otherwise, it returns None.

        Returns:
            GraphVertex | None: A GraphVertex instance if the table has vertex
            information, otherwise None.
        """
        if self.table.info.get("vertex", True):
            return GraphVertex(table=self.table)
        return None

    @computed_field
    def edges(self) -> list["GraphEdge"]:
        """
        Get the edges for a given table.

        Returns:
            list[GraphEdge]: A list of GraphEdge objects representing the edges
            in the graph. The edges are determined based on whether the table
            is a normal table or an association table.

        For a normal table:
            - Edges are created from the vertex representing the table itself

        For an association table:
            - Edges are created between each of the foreign keys in the table.
        """
        edges = []
        if self.vertex:
            """
            Normal table
            Edges are created from the vertex, representing the table itself, 
            to each of the foreign keys in the table.
            """
            start_vertex = GraphVertex(table=self.table)
            start_column = self.table.columns["id"]
            for column in self.table.columns:
                if not column.foreign_keys:
                    continue
                for fk in column.foreign_keys:
                    if start_column.name == column.name:
                        continue
                    end_vertex = GraphVertex(table=fk.column.table)
                    label = column.info.get("edge", "")
                    edges.append(
                        GraphEdge(
                            column=start_column,
                            table=self.table,
                            start_vertex=start_vertex,
                            end_vertex=end_vertex,
                            label=label,
                        )
                    )
        else:
            """
            Association table
            Edges are created between each of the foreign keys in the table.
            """
            for fk in self.table.foreign_keys:
                start_vertex = GraphVertex(table=fk.column.table)
                for column in self.table.columns:
                    if fk.parent.name == column.name:
                        continue
                    for _fk in column.foreign_keys:
                        end_vertex = GraphVertex(table=_fk.column.table)
                        label = column.info.get("edge", "")
                        edges.append(
                            GraphEdge(
                                column=_fk.column,
                                table=self.table,
                                start_vertex=start_vertex,
                                end_vertex=end_vertex,
                                label=label,
                            )
                        )
        return edges

    def create_table_sql(self) -> str:
        """
        Generates SQL statements to create a table in the graph.

        This method generates SQL statements to create a table in a graph database.
        The table is created based on the vertex information of the table.
        If the table is a normal table, the vertex is created with an index on the 'id' column.
        If the table is an association table, the edges are created between the foreign keys.

        Returns:
            str: The SQL statement to create the table in the graph.
        """
        if self.vertex:
            sql = self.vertex.create_vlabel_sql()
        else:
            sql = "\n".join([e.create_elabel_sql() for e in self.edges])

        sql = "\n".join(
            [
                sql,
                self.create_insert_sql(),
                self.create_update_sql(),
                self.create_delete_sql(),
                self.create_truncate_sql(),
            ]
        )
        return textwrap.dedent(sql)

    def create_insert_sql(self) -> str:
        """Creates a new vertex record when a new relational table record is inserted"""
        prop_key_str = ""
        prop_val_str = ""
        edge_sql = ""
        if self.edges:
            edge_sql = "\n".join([e.edge_sql() for e in self.edges])
        if self.vertex:
            if self.vertex.properties:
                prop_key_str = ", ".join(
                    f"{prop.name}: %s" for prop in self.vertex.properties
                )
                prop_val_str = ", " + ", ".join(
                    [prop.data_type for prop in self.vertex.properties]
                )
            sql = textwrap.dedent(
                f"""
                EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                    CREATE (v:{self.vertex.label} {{{prop_key_str}}})
                $$) AS (a agtype);'{prop_val_str});
                {edge_sql}
                RETURN NEW;
                """
            )
        else:
            sql = textwrap.dedent(
                f"""
                {edge_sql}
                RETURN NEW;
                """
            )
        sql_string = self.create_sql_stmt(
            "insert_vertex",
            sql,
            operation="INSERT",
            include_trigger=True,
        )
        return textwrap.dedent(sql_string)

    def create_update_sql(self) -> str:
        """Updates an existing vertex record when its relational table record is updated"""
        property_keys_str = ""
        property_values_str = ""
        edge_sql = ""
        if self.edges:
            edge_sql = "\n".join([e.edge_sql() for e in self.edges])
        if self.vertex:
            if self.vertex.properties:
                property_keys_str = "SET" + ", ".join(
                    [prop.name for prop in self.vertex.properties]
                )
                property_values_str = ", " + ", ".join(
                    [prop.data_type for prop in self.vertex.properties]
                )
            sql = textwrap.dedent(
                f"""
                EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                    MATCH (v:{self.vertex.label})
                    WHERE (v.id = %s)
                    {property_keys_str}
                $$) AS (a agtype);', quote_nullable(NEW.id){property_values_str});
                RETURN NEW;
                """
            )
        else:
            sql = textwrap.dedent(
                f"""
                {edge_sql}
                RETURN NEW;
                """
            )
        sql_string = self.create_sql_stmt(
            "update_vertex",
            sql,
            include_trigger=True,
        )
        return textwrap.dedent(sql_string)

    def create_delete_sql(self) -> str:
        """Deleted an existing vertex record when its relational table record is deleted"""
        edge_sql = ""
        if self.edges:
            edge_sql = "\n".join([e.edge_sql() for e in self.edges])
        if self.vertex:
            sql = textwrap.dedent(
                f"""
                EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                    MATCH (v:{self.vertex.label})
                    WHERE (v.id = %s)
                    DETACH DELETE v
                $$) AS (a agtype);', quote_nullable(OLD.id));
                RETURN OLD;
                """
            )
        else:
            sql = textwrap.dedent(
                f"""
                {edge_sql}
                RETURN OLD;
                """
            )
        sql_string = self.create_sql_stmt(
            "delete_vertex",
            sql,
            operation="DELETE",
            include_trigger=True,
        )
        return textwrap.dedent(sql_string)

    def create_truncate_sql(self) -> str:
        """Deletes all corresponding vertices for a relation table when the table is truncated"""
        edge_sql = ""
        if self.edges:
            edge_sql = "\n".join([e.edge_sql() for e in self.edges])
        if self.vertex:
            sql = textwrap.dedent(
                f"""
                EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                    MATCH (v:{self.vertex.label})
                    DETACH DELETE v
                $$) AS (a agtype);');
                RETURN OLD;
                """
            )
        else:
            sql = textwrap.dedent(
                f"""
                {edge_sql}
                RETURN OLD;
                """
            )
        sql_string = self.create_sql_stmt(
            "truncate_vertex",
            sql,
            operation="truncate",
            for_each="STATEMENT",
            include_trigger=True,
        )
        return textwrap.dedent(sql_string)
