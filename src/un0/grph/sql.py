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

    def create_sql_function(
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
        return f"""
            SELECT ag_catalog.create_vlabel('graph', '{self.label}');
            CREATE INDEX ON graph."{self.label}" (id);
        """


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

    def create_edge_sql(self) -> str:
        """
        Creates the Cypher statements to create edges between vertices.

        This method generates SQL statements to create edges in a graph database.
        The edges are created between vertices based on the foreign keys of the table.
        If the table is an association table, the edges may have additional properties
        derived from non-foreign key columns in the table.

        Returns:
            str: The SQL statement to create the edges.
        """
        if not self.properties:
            return textwrap.dedent(
                f"""
                EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                    MATCH (v:{self.start_vertex.label} {{id: %s}})
                    MATCH (w:{self.end_vertex.label} {{id: %s}})
                    CREATE (v)-[e:{self.label}]->(w)
                $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type});
                """
            )
        return textwrap.dedent(
            f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                CREATE (v)-[e:{self.edge_name} {{{self.properties.keys()}}}] ->(w)
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type}, {self.properties.values()});
            """
        )

    def create_elabel_sql(self) -> str:
        """
        Generates an SQL query string to create an edge label and an index for a graph.

        Returns:
            str: A formatted SQL query string that creates an edge label in the 'graph' schema
             and an index on the 'start_id' and 'end_id' columns of the created label.
        """
        return f"""
            SELECT ag_catalog.create_elabel('graph', '{self.label}');
            CREATE INDEX ON graph."{self.label}"(start_id, end_id);
        """


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
        """Get the edges for a given table"""
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
                        print("Skipping")
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


'''
def create_edge_statements(
    edges: list[GraphEdge],
    table_name: str,
    property_names: str | None = None,
    property_values: str | None = None,
) -> str:
    """Creates the cypher statements to create edges between vertices

    Edges are created between vertices based on the foreign keys of the table.
    Edges created for association tables may have properties, e.g. non-foreign key
    columns in the table.
    """
    # for edge in edges:
    #    if edge.edge_name == "":
    #        raise ValueError(
    #            f"{table_name} {edge.start_vertex_label}: Edge name is required"
    #        )
    if property_names is None:
        sql_string = " ".join(
            [
                textwrap.dedent(
                    f"""
                EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                    MATCH (v:{edge.start_vertex_label} {{id: %s}})
                    MATCH (w:{edge.end_vertex_label} {{id: %s}})
                    CREATE (v)-[e:{edge.edge_name}]->(w)
                $$) AS (e agtype);', {edge.start_vertex_data_type}, {edge.end_vertex_data_type});
                """
                )
                for edge in edges
            ]
        )
    else:
        sql_string = " ".join(
            [
                textwrap.dedent(
                    f"""
                EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                    MATCH (v:{edge.start_vertex_label} {{id: %s}})
                    MATCH (w:{edge.end_vertex_label} {{id: %s}})
                    CREATE (v)-[e:{edge.edge_name} {{{property_names}}}] ->(w)
                $$) AS (e agtype);', {edge.start_vertex_data_type}, {edge.end_vertex_data_type}, {property_values});
                """
                )
                for edge in edges
            ]
        )
    return textwrap.dedent(sql_string)


# INSERT Vertex Function and Trigger
def insert_vertex_functions_and_triggers(table: Table, db_name=sttngs.DB_NAME) -> str:
    """Creates a new vertex record when a new relational table record is inserted"""
    table_name = table.name
    edges: list[GraphEdge] = []
    property_names, property_values = get_properties(table, update=False)
    edges = get_table_edges(table)
    vertex_label = convert_snake_to_capital_word(table_name)
    edge_creation_statements = create_edge_statements(edges, table_name)
    if property_names:
        execution_string = f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                CREATE (v:{vertex_label} {{{property_names}}})
            $$) AS (a agtype);', {property_values});
            {edge_creation_statements}
            RETURN NEW;
            """
    else:
        execution_string = f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                CREATE (v:{vertex_label})
            $$) AS (a agtype);');
            {edge_creation_statements}
            RETURN NEW;
            """
    sql_string = create_sql_function(
        table,
        "insert_vertex",
        execution_string,
        operation="INSERT",
        include_trigger=True,
        db_name=db_name,
    )
    return textwrap.dedent(sql_string)


# UPDATE Vertex Function and Trigger
def update_vertex_functions_and_triggers(table: Table, db_name=sttngs.DB_NAME) -> str:
    """Updates an existing vertex record when its relational table record is updated"""
    table_name = table.name
    vertex_label = convert_snake_to_capital_word(table_name)
    property_names, property_values = get_properties(table, update=True)
    execution_string = f"""
        EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
            MATCH (v:{vertex_label})
            WHERE (v.id = %s)
            SET {property_names}
        $$) AS (a agtype);', quote_nullable(NEW.id), {property_values});
        RETURN NEW;
        """
    sql_string = create_sql_function(
        table,
        "update_vertex",
        execution_string,
        include_trigger=True,
        db_name=db_name,
    )
    return textwrap.dedent(sql_string)


# DELETE Vertex Function and Trigger
def delete_vertex_functions_and_triggers(table: Table, db_name=sttngs.DB_NAME) -> str:
    """Deleted an existing vertex record when its relational table record is deleted"""
    table_name = table.name
    vertex_label = convert_snake_to_capital_word(table_name)
    execution_string = f"""
        EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
            MATCH (v:{vertex_label})
            WHERE (v.id = %s)
            DETACH DELETE v
        $$) AS (a agtype);', quote_nullable(OLD.id));
        RETURN NEW;
        """
    sql_string = create_sql_function(
        table,
        "delete_vertex",
        execution_string,
        operation="DELETE",
        include_trigger=True,
        db_name=db_name,
    )
    return textwrap.dedent(sql_string)


# TRUNCATE Vertex Function and Trigger
def truncate_vertex_functions_and_triggers(table: Table, db_name=sttngs.DB_NAME) -> str:
    """Deletes all corresponding vertices for a relation table when the table is truncated"""
    table_name = table.name
    vertex_label = convert_snake_to_capital_word(table_name)
    execution_string = f"""
        EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
            MATCH (v:{vertex_label})
            DELETE v
        $$) AS (a agtype);');
        RETURN NEW;
        """
    sql_string = create_sql_function(
        table,
        "truncate_vertex",
        execution_string,
        operation="TRUNCATE",
        for_each="STATEMENT",
        include_trigger=True,
        db_name=db_name,
    )
    return textwrap.dedent(sql_string)


# EDGE WITH PROPERTIES FUNCTIONS AND TRIGGERS


def edge_properties(table: Table, update: bool = True) -> tuple[str, str]:
    """Get the graph properties for an association table"""
    property_names = []
    property_values = []

    for column in table.columns:
        property_names.append(f"{column.name}: %s")
        property_values.append(get_column_type(column, update=update))

    if update:
        return ", ".join([f"v.{name}" for name in property_names]), ", ".join(
            [f"NEW.{value}" for value in property_values]
        )
    return ", ".join(property_names), ", ".join(property_values)


def edge_w_props_vertices_old(table: Table, update: bool = True) -> list:
    """Returns the vertices for an association table"""
    start_vertices = []
    end_vertices = []
    edges = []
    for column in table.columns:
        for fk in column.foreign_keys:
            start_vertices.append(
                (
                    convert_snake_to_capital_word(fk.column.table.name),
                    get_column_type(column, update=update),
                )
            )
            end_vertices.append(
                (
                    convert_snake_to_capital_word(fk.column.table.name),
                    get_column_type(column, update=update),
                )
            )
    for start_vertex in start_vertices:
        for end_vertex in end_vertices:
            if start_vertex[0] != end_vertex[0]:
                edges.append(
                    GraphEdge(
                        start_vertex_label=start_vertex[0],
                        start_vertex_data_type=start_vertex[1],
                        end_vertex_label=end_vertex[0],
                        end_vertex_data_type=end_vertex[1],
                        edge_name=table.info.get("edge", ""),
                    )
                )
    return edges


def edge_w_props_vertices(table: Table, update: bool = True) -> GraphEdge:
    """Returns the vertices for an association table"""
    return GraphEdge(
        start_vertex_label=convert_snake_to_capital_word(
            list(table.foreign_keys)[0].column.table.name
        ),
        start_vertex_data_type=get_column_type(table.columns[0], update=update),
        end_vertex_label=convert_snake_to_capital_word(
            list(table.foreign_keys)[1].column.table.name
        ),
        end_vertex_data_type=get_column_type(table.columns[1], update=update),
        edge_name=table.info.get("edge", ""),
    )


def edge_with_properties(table: Table, update: bool = True) -> str:
    """Creates the edge table definition for association tables"""
    edge = edge_w_props_vertices(table, update=update)
    property_names, property_values = edge_properties(table, update=update)
    edge_creation_statements = create_edge_statements(
        [edge],
        table.name,
        property_names=property_names,
        property_values=property_values,
    )
    return edge_creation_statements


def insert_edge_w_props_functions_and_triggers(table: Table) -> str:
    """Create a new edge record when a new association table record is inserted"""
    _execution_string = " ".join(
        [
            f"""
                EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                    MATCH (a:{edge.start_vertex_label}), (b:{edge.end_vertex_label})
                    WHERE (a.id = %s AND b.id = %s)
                    CREATE (a)-[e:{edge.edge_name}]->(b)
                $$) AS (e agtype);', {edge.start_vertex_data_type}, {edge.end_vertex_data_type});
                RETURN NEW;
                """
            for edge in edge_w_props_vertices_old(table, update=False)
        ]
    )
    execution_string = textwrap.dedent(_execution_string)

    sql_string = create_sql_function(
        table,
        "insert_edge",
        execution_string,
        operation="INSERT",
        include_trigger=True,
    )
    return textwrap.dedent(sql_string)


def get_edge_match_statements(table: Table):
    """Get the match statements for an association table's edge record from the fks
    Works with any number of foreign keys in the association table.
    """
    edge_label = table.info.get("edge", "")
    foreign_keys = []
    vertex_keys = []
    vertex = "a"
    for column in table.columns:
        for fk in column.foreign_keys:
            if column.name not in foreign_keys:
                foreign_keys.append(column.name)
                vertex_keys.append(
                    f"{vertex}:{fk.column.table.name} {{{vertex}.{column.name}: %s}}"
                )
                vertex = chr(ord(vertex) + 1)

    match_stmt = "MATCH "
    for num, name in enumerate(vertex_keys):
        if num == 0:
            match_stmt += f"({name})-[\\:{edge_label}]"
        elif num < len(vertex_keys) - 1:
            match_stmt += f"-({name})-[\\:{edge_label}]"
        else:
            match_stmt += f"-({name})"
    return match_stmt


def delete_edge_w_props_functions_and_triggers(table: Table) -> str:
    """Deleted an existing edge record when its association table record is deleted"""
    match_stmt = get_edge_match_statements(table)
    _execution_string = f"""
        EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
            {match_stmt}
            delete
        $$) AS (a agtype);', quote_nullable(OLD.id));
        RETURN NEW;
        """
    execution_string = textwrap.dedent(_execution_string)
    sql_string = create_sql_function(
        table,
        "delete_edge",
        execution_string,
        operation="DELETE",
        include_trigger=True,
    )
    return textwrap.dedent(sql_string)


def truncate_edge_w_props_functions_and_triggers(table: Table) -> str:
    """Truncate all edges for an association table"""
    edge_label = table.info.get("edge", "")
    _execution_string = f"""
        EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
            MATCH (()-[e:{edge_label}]-())
            DELETE e
        $$) AS (a agtype);');
        RETURN NEW;
        """
    execution_string = textwrap.dedent(_execution_string)
    sql_string = create_sql_function(
        table,
        "truncate_edge",
        execution_string,
        operation="TRUNCATE",
        for_each="STATEMENT",
        include_trigger=True,
    )
    return textwrap.dedent(sql_string)
'''
