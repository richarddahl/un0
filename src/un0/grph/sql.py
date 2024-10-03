# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import textwrap

from pydantic import BaseModel

from sqlalchemy import Table, Column

from un0.utilities import convert_snake_to_capital_word
from un0.config import settings as sttngs


def init_settings():
    sttngs.__init__()


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


def create_vlabel(table_name):
    return f"SELECT ag_catalog.create_vlabel('graph', '{convert_snake_to_capital_word(table_name)}');"


def create_elabel(edge_name):
    return f"SELECT ag_catalog.create_elabel('graph', '{edge_name}');"


def get_column_type(column: Column, prefix: str = "NEW", update: bool = True) -> str:
    """Get the column type for a given column"""
    if update is False:
        if issubclass(column.type.python_type, list):
            return f"to_jsonb({prefix}.{column.name})"
        if issubclass(column.type.python_type, str):
            return f"quote_nullable({prefix}.{column.name}::{column.type})"
        if issubclass(column.type.python_type, bool):
            return f"quote_nullable({prefix}.{column.name})"
        if issubclass(column.type.python_type, int):
            return f"quote_nullable({prefix}.{column.name}::{column.type})"
        if issubclass(column.type.python_type, datetime.datetime):
            return f"quote_nullable({prefix}.{column.name}::{column.type})"
        return f"quote_nullable({prefix}.{column.name}::{column.type})"
    return f"quote_nullable({prefix}.{column.name})"


def get_column_properties(
    column: Column, update: bool = True
) -> tuple[str, str] | None:
    if column.foreign_keys:
        return None
    if column.info.get("edge", False) is not False:
        return None
    if column.info.get("graph_properties", False) is True:
        return get_column_properties(column, update=update)
    if update:
        return f"{column.name} = %s", get_column_type(column, update=update)
    return f"{column.name}: %s", get_column_type(column, update=update)


class EdgeData(BaseModel):
    """Holds the data for defining an edge"""

    start_vertex_label: str
    start_vertex_data_type: str
    end_vertex_label: str
    end_vertex_data_type: str
    edge_name: str


def vertex_properties(table: Table, update: bool = True) -> tuple[str, str]:
    """Get the graph properties for a given table"""
    property_names = []
    property_values = []

    for column in table.columns:
        if column.info.get("exclude_from_graph_properties", False) is True:
            continue
        if column.foreign_keys:
            for fk in column.foreign_keys:
                if (
                    column.info.get("graph_properties", False) is True
                    or column.name == "id"
                ):
                    for fk_column in fk.column.table.columns:
                        col_props_and_vals = get_column_properties(
                            fk_column, update=update
                        )
                        if col_props_and_vals is not None:
                            property_names.append(col_props_and_vals[0])
                            property_values.append(col_props_and_vals[1])
        else:
            col_props_and_vals = get_column_properties(column, update=update)
            if col_props_and_vals is not None:
                property_names.append(col_props_and_vals[0])
                property_values.append(col_props_and_vals[1])

    if update:
        return ", ".join([f"v.{name}" for name in property_names]), ", ".join(
            property_values
        )
    return ",".join(property_names), ",".join(property_values)


def vertex_edges(table: Table, update: bool = True) -> list:
    """Get the graph edges (based on foreign keys) for a given table"""
    table_name = table.name
    edges = []

    for column in table.columns:
        if column.foreign_keys:
            for fk in column.foreign_keys:
                edges.append(
                    EdgeData(
                        start_vertex_label=convert_snake_to_capital_word(table_name),
                        start_vertex_data_type=get_column_type(
                            table.columns["id"], update=update
                        ),
                        end_vertex_label=convert_snake_to_capital_word(
                            fk.column.table.name
                        ),
                        end_vertex_data_type=get_column_type(fk.column, update=update),
                        edge_name=column.info.get("edge", ""),
                    )
                )
    return edges


def create_edge_statements(
    edges: list[EdgeData],
    table_name: str,
    property_names: str | None = None,
    property_values: str | None = None,
) -> str:
    """Creates the cypher statements to create edges between vertices"""
    for edge in edges:
        if edge.edge_name == "":
            raise ValueError(
                f"{table_name} {edge.start_vertex_label}: Edge name is required"
            )
    if property_names is None:
        sql_string = " ".join(
            [
                textwrap.dedent(
                    f"""
                EXECUTE format('SELECT * FROM cypher(''graph'', $$
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
                EXECUTE format('SELECT * FROM cypher(''graph'', $$
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


def function_body(
    table: Table,
    function_name: str,
    execution_string: str,
    operation: str = "UPDATE",
    for_each: str = "ROW",
    include_trigger: bool = False,
    db_name: str = sttngs.DB_NAME,
) -> str:
    table_name = table.name
    schema_name = table.schema
    func_string = f"""
        CREATE OR REPLACE FUNCTION {schema_name}.{table_name}_{function_name}()
            RETURNS TRIGGER
            LANGUAGE plpgsql
            VOLATILE
        AS $BODY$
        BEGIN
            SET ROLE {db_name}_admin;
            {execution_string}
        END;
        $BODY$;
    """
    trigger_string = f"""
        CREATE OR REPLACE TRIGGER {table_name}_{function_name}_trigger
            AFTER {operation}
            ON {schema_name}.{table_name}
            FOR EACH {for_each}
            EXECUTE FUNCTION {schema_name}.{table_name}_{function_name}();
    """
    sql_str = f"{func_string}\n{trigger_string}" if include_trigger else func_string
    return textwrap.dedent(sql_str)


# INSERT Vertex Function and Trigger
def insert_vertex_functions_and_triggers(table: Table, db_name=sttngs.DB_NAME) -> str:
    """Creates a new vertex record when a new relational table record is inserted"""
    table_name = table.name
    edges: list[EdgeData] = []
    property_names, property_values = vertex_properties(table, update=False)
    edges = vertex_edges(table)
    vertex_label = convert_snake_to_capital_word(table_name)
    edge_creation_statements = create_edge_statements(edges, table_name)
    execution_string = f"""
        EXECUTE format('SELECT * FROM cypher(''graph'', $$
            CREATE (v:{vertex_label} {{{property_names}}})
        $$) AS (a agtype);', {property_values});
        {edge_creation_statements}
        RETURN NEW;
        """
    sql_string = function_body(
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
    property_names, property_values = vertex_properties(table, update=True)
    execution_string = f"""
        EXECUTE format('SELECT * FROM cypher(''graph'', $$
            MATCH (v:{vertex_label})
            WHERE (v.id = %s)
            SET {property_names}
        $$) AS (a agtype);', quote_nullable(NEW.id), {property_values});
        RETURN NEW;
        """
    sql_string = function_body(
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
        EXECUTE format('SELECT * FROM cypher(''graph'', $$
            MATCH (v:{vertex_label})
            WHERE (v.id = %s)
            DETACH DELETE v
        $$) AS (a agtype);', quote_nullable(OLD.id));
        RETURN NEW;
        """
    sql_string = function_body(
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
        EXECUTE format('SELECT * FROM cypher(''graph'', $$
            MATCH (v:{vertex_label})
            DELETE v
        $$) AS (a agtype);');
        RETURN NEW;
        """
    sql_string = function_body(
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
                    EdgeData(
                        start_vertex_label=start_vertex[0],
                        start_vertex_data_type=start_vertex[1],
                        end_vertex_label=end_vertex[0],
                        end_vertex_data_type=end_vertex[1],
                        edge_name=table.info.get("edge", ""),
                    )
                )
    return edges


def edge_w_props_vertices(table: Table, update: bool = True) -> EdgeData:
    """Returns the vertices for an association table"""
    return EdgeData(
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
                EXECUTE format('SELECT * FROM cypher(''graph'', $$
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

    sql_string = function_body(
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
        EXECUTE format('SELECT * FROM cypher(''graph'', $$
            {match_stmt}
            delete
        $$) AS (a agtype);', quote_nullable(OLD.id));
        RETURN NEW;
        """
    execution_string = textwrap.dedent(_execution_string)
    sql_string = function_body(
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
        EXECUTE format('SELECT * FROM cypher(''graph'', $$
            MATCH (()-[e:{edge_label}]-())
            DELETE e
        $$) AS (a agtype);');
        RETURN NEW;
        """
    execution_string = textwrap.dedent(_execution_string)
    sql_string = function_body(
        table,
        "truncate_edge",
        execution_string,
        operation="TRUNCATE",
        for_each="STATEMENT",
        include_trigger=True,
    )
    return textwrap.dedent(sql_string)
