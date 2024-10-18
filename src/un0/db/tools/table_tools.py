# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import textwrap

from datetime import datetime, date, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, computed_field

from sqlalchemy import Table, Column

from un0.utilities import convert_snake_to_capital_word
from un0.fltr.enums import (  # type: ignore
    GraphType,
    EdgeDirection,
    Include,
    Match,
    Lookup,
    ColumnSecurity,
    related_lookups,
    numeric_lookups,
    string_lookups,
)
from un0.config import settings as sttngs


class TableTool(BaseModel):
    """
    TableTool is a Pydantic model that represents the schema of a database table. It includes various computed fields and methods to generate SQL statements for configuring the table, enabling auditing, and creating triggers.

    Attributes:
        table (Table): The SQLAlchemy Table object representing the database table.
        model_config (ConfigDict): Configuration for the Pydantic model, allowing arbitrary types.
        table_schema (str): The schema of the table.
        table_name (str): The name of the table.
        schema_table_name (str): The full name of the table including schema.
        rls_policy (str): The row-level security policy for the table.
        graph (bool): Indicates if the table is part of a graph.
        vertex (VertexTool): The vertex schema if the table is a vertex.
        edges (list[EdgeTool] | None): The edges schema if the table has foreign keys.
        properties (list[PropertyTool] | None): The properties schema for the table columns.

    Methods:
        configuration_sql() -> str: Generates SQL statements for configuring the table.
        create_tabletype_record() -> str: Generates SQL to create a table type record.
        enable_rls() -> str: Generates SQL to enable row-level security for the table.
        create_set_owner_and_modified_trigger() -> str: Generates SQL to create a trigger for setting owner and modified fields.
        create_history_table_triggercreate_set_owner_and_modified_trigger() -> str: Generates SQL to create a trigger for setting owner and modified fields.
        create_validate_delete_trigger() -> str: Generates SQL to create a trigger for validating deletes.
        change_table_owner_and_set_privileges() -> str: Generates SQL to change table owner and set privileges.
        enable_auditing() -> str: Generates SQL to enable auditing for the table.
        create_history_table() -> str: Generates SQL to create a history table for auditing.
        create_history_table_trigger() -> str: Generates SQL to create a trigger for the history table.
        create_sql_function(function_name: str, function_string: str, operation: str = "UPDATE", for_each: str = "ROW", include_trigger: bool = False) -> str: Creates a SQL function and optionally a trigger for a PostgreSQL database.
    """

    # filter_set: "FilterSetSchema" = None
    # table_name: str <- computed_field
    # table_schema: str <- computed_field
    # schema_table_name: str <- computed_field
    # rls_policy: str <- computed_field
    # in_graph: bool <- computed_field
    # vertex: VertexTool <- computed_field
    # edges: EdgeTool <- computed_field
    # properties: PropertyTool <- computed_field

    table: Table

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def table_schema(self) -> str:
        return self.table.schema

    @computed_field
    def table_name(self) -> str:
        return self.table.name

    @computed_field
    def schema_table_name(self) -> str:
        return f"{self.table_schema}.{self.table_name}"

    @computed_field
    def rls_policy(self) -> str:
        return self.table.info.get("rls_policy", "UserGroup")

    @computed_field
    def graph(self) -> bool:
        return self.table.info.get("in_graph", True)

    @computed_field
    def vertex(self) -> bool:
        """
        Determines if the table is a vertex and returns a VertexTool instance if true.

        Returns:
            VertexTool: An instance of VertexTool if the table is a vertex.
            bool: False if the table is not a vertex.
        """
        if self.table.info.get("vertex", True) is not False:
            return VertexTool(
                table=self.table, column=self.table.primary_key.columns[0]
            )

    @computed_field
    def edges(self) -> list["EdgeTool"] | None:
        """
        Generates a list of EdgeTool objects representing the edges in the database schema.

        This method iterates over the foreign keys of the table and their corresponding columns to create
        EdgeTool instances. Each EdgeTool represents a relationship between two vertices (start and end)
        in the schema.

        Returns:
            list[EdgeTool] | None: A list of EdgeTool objects if any edges are found, otherwise None.
        """
        edges = []
        for fk in self.table.foreign_keys:
            for column in self.table.columns:
                if fk.parent.name == column.name:
                    continue
                for _fk in column.foreign_keys:
                    edges.append(
                        EdgeTool(
                            table=self.table,
                            to_column=column,
                            start_vertex=VertexTool(
                                table=self.table,
                                column=fk.parent,
                            ),
                            end_vertex=VertexTool(
                                table=fk.column.table,
                                column=fk.column,
                            ),
                        )
                    )
        return edges

    @computed_field
    def properties(self) -> list["PropertyTool"] | None:
        """
        Retrieves a list of PropertyTool objects for each column in the table.

        Returns:
            list[PropertyTool] | None: A list of PropertyTool objects representing
            the properties of each column in the table, or None if there are no columns.
        """
        props = []
        for column in self.table.columns:
            props.append(PropertyTool(table=self.table, column=column))
        return props

    # Functions to generate sql statements
    def configuration_sql(self) -> str:
        """
        Generates the SQL configuration string for setting up the database table.

        This method constructs a SQL string that includes:
        - Setting the role to the database admin.
        - Changing the table owner and setting privileges.
        - Creating a table type record.
        - Optionally creating triggers for setting owner and modified timestamps, and validating deletes if the table has an "owner_id" column.
        - Enabling auditing based on the table's audit type:
            - "basic": Enables default auditing.
            - "history": Creates a history table and trigger for auditing changes.
        - Creating vertex and edge triggers if applicable.
        - Creating filter field SQL for properties.

        Returns:
            str: The complete SQL configuration string.
        """
        sql = textwrap.dedent(
            f"SET ROLE {sttngs.DB_NAME}_admin;"
            f"\n{self.change_table_owner_and_set_privileges()}"
            f"\n{self.create_tabletype_record()}"
        )

        if "owner_id" in self.table.columns:
            sql += f"\n{textwrap.dedent(self.create_set_owner_and_modified_trigger())}"
            sql += f"\n{textwrap.dedent(self.create_validate_delete_trigger())}"

        # Enables auditing for the table if the audit_type is not set to None in the tables info dictionary.
        # If the audit_type is set to "history", then the history table and trigger are created for the table
        #    - A duplicate of the table is created as audit.[table_schema]_[table_name]
        #    - The trigger is created to insert a duplicate record into the history table after insert or update
        #    - A function is created to restore a record from the history table to the actual table
        # If the audit_type is set to None, then no un0 auditing occurs.
        # Otherwise, the audit trigger is created as a default:
        #    - all changes will be audited in the audit.record_version table, using supabase_audit.
        audit_type = self.table.info.get("audit", "basic")
        if audit_type == "basic":
            sql += f"\n{textwrap.dedent(self.enable_auditing())}"
        elif audit_type == "history":
            sql += f"\n{textwrap.dedent(self.create_history_table())}"
            sql += f"\n{textwrap.dedent(self.create_history_table_trigger())}"

        # Create the vertex and edge triggers
        if self.vertex:
            sql += f"\n{textwrap.dedent(self.vertex.create_sql())}"
        else:
            for edge in self.edges:
                sql += f"\n{textwrap.dedent(edge.create_sql())}"
        for prop in self.properties:
            sql += f"\n{textwrap.dedent(prop.create_filter_field_sql())}"

        # if self.table.info.get("rls_policy", None) is not None:
        #    sql += f"\n{textwrap.dedent(self.enable_rls())}"
        #
        return sql

    def create_tabletype_record(self) -> str:
        """
        Generates an SQL statement to insert a record into the `un0.tabletype` table.

        This method creates a SQL INSERT statement that adds a new record to the
        `un0.tabletype` table with the schema and name provided by the instance's
        `table_schema` and `table_name` attributes.

        Returns:
            str: A formatted SQL INSERT statement as a string.
        """
        return textwrap.dedent(
            f"""
            -- Create the tabletype record
            INSERT INTO un0.tabletype (schema, name)
            VALUES ('{self.table_schema}', '{self.table_name}');
            """
        )

    def enable_rls(self) -> str:
        """
        Generates SQL statements to enable and enforce Row Level Security (RLS)
        on a specified table.

        Returns:
            str: A string containing the SQL statements to enable and force RLS
                 for the table.
        """
        return textwrap.dedent(
            f"""
            -- Enable RLS for the table
            ALTER TABLE {self.schema_table_name} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {self.schema_table_name} FORCE ROW LEVEL SECURITY;
            """
        )

    def create_set_owner_and_modified_trigger(self) -> str:
        """
        Generates a SQL trigger creation statement for setting the owner and
        modified timestamp on a specified table.

        This method creates a trigger named 'set_owner_and_modified_trigger'
        that will be executed before any INSERT or UPDATE operation on the
        table specified by `self.schema_table_name`. The trigger will call
        the function `un0.set_owner_and_modified()` to set the owner and
        modified timestamp.

        Returns:
            str: A SQL statement for creating the trigger.
        """
        return textwrap.dedent(
            f"""
            CREATE TRIGGER set_owner_and_modified_trigger
            BEFORE INSERT OR UPDATE ON {self.schema_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION un0.set_owner_and_modified();
            """
        )

    def create_history_table_triggercreate_set_owner_and_modified_trigger(self) -> str:
        """
        Generates a SQL trigger creation statement for setting the owner and modified timestamp.

        This method returns a SQL statement that creates a trigger named
        `set_owner_and_modified_trigger`. The trigger is executed before
        any INSERT or UPDATE operation on the specified table, and it
        calls the `un0.set_owner_and_modified()` function.

        Returns:
            str: A SQL statement for creating the trigger.
        """
        return textwrap.dedent(
            f"""
            CREATE TRIGGER set_owner_and_modified_trigger
            BEFORE INSERT OR UPDATE ON {self.schema_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION un0.set_owner_and_modified();
            """
        )

    def create_validate_delete_trigger(self) -> str:
        """
        Generates a SQL trigger creation statement for validating deletions.

        This method creates a SQL trigger named `validate_delete_trigger` that is
        executed before a delete operation on the specified table. The trigger
        calls the `un0.validate_delete()` function to perform validation.

        Returns:
            str: A SQL statement for creating the `validate_delete_trigger`.
        """
        return textwrap.dedent(
            f"""
            CREATE TRIGGER validate_delete_trigger 
            BEFORE DELETE ON {self.schema_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION un0.validate_delete();
            """
        )

    def change_table_owner_and_set_privileges(self) -> str:
        """
        Generates a SQL command to change the owner of a table and set privileges.

        The generated SQL command will:
        - Change the owner of the table to the admin user of the database.
        - Grant SELECT privileges to the reader and writer roles.
        - Grant INSERT, UPDATE, and DELETE privileges to the writer role.

        Returns:
            str: A formatted SQL command string.
        """
        return textwrap.dedent(
            f"""
            ALTER TABLE {self.schema_table_name} OWNER TO {sttngs.DB_NAME}_admin;
            GRANT SELECT ON {self.schema_table_name} TO
                {sttngs.DB_NAME}_reader,
                {sttngs.DB_NAME}_writer;
            GRANT INSERT, UPDATE, DELETE ON {self.schema_table_name} TO
                {sttngs.DB_NAME}_writer;
            """
        )

    def enable_auditing(self) -> str:
        """
        Generates a SQL query to enable auditing for the specified table.

        Returns:
            str: A SQL query string that enables auditing for the table.
        """
        return textwrap.dedent(
            f"""
            -- Enable auditing for the table
            SELECT audit.enable_tracking('{self.schema_table_name}'::regclass);
            """
        )

    def create_history_table(self) -> str:
        """
        Creates a SQL statement to generate a history table for auditing purposes.

        The history table will be created in the 'audit' schema and will have the same structure
        as the original table, but without any data. Additionally, it will have an auto-incrementing
        primary key column and two indexes: one on the primary key and another on the combination
        of 'id' and 'modified_at' columns.

        Returns:
            str: A SQL statement to create the history table.
        """
        return textwrap.dedent(
            f"""
            CREATE TABLE audit.{self.table_schema}_{self.table_name}
            AS (SELECT * FROM {self.table_schema}.{self.table_name})
            WITH NO DATA;

            ALTER TABLE audit.{self.table_schema}_{self.table_name}
            ADD COLUMN pk INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;

            CREATE INDEX {self.table_schema}_{self.table_name}_pk_idx
            ON audit.{self.table_schema}_{self.table_name} (pk);

            CREATE INDEX {self.table_schema}_{self.table_name}_id_modified_at_idx
            ON audit.{self.table_schema}_{self.table_name} (id, modified_at);
            """
        )

    def create_history_table_trigger(self) -> str:
        """
        Generates a SQL trigger function and trigger for auditing changes to a table.

        This method creates a PostgreSQL function and trigger that logs changes to a specified table
        into an audit table. The function and trigger are created within the same schema as the target table.

        Returns:
            str: A string containing the SQL statements to create the audit function and trigger.
        """
        return textwrap.dedent(
            f"""
            CREATE OR REPLACE FUNCTION {self.table_schema}.{self.table_name}_audit()
            RETURNS TRIGGER
            LANGUAGE plpgsql
            SECURITY DEFINER
            AS $$
            BEGIN
                INSERT INTO audit.{self.table_schema}_{self.table_name}
                SELECT *
                FROM {self.table_schema}.{self.table_name}
                WHERE id = NEW.id;
                RETURN NEW;
            END;
            $$;

            CREATE OR REPLACE TRIGGER {self.table_name}_audit_trigger
            AFTER INSERT OR UPDATE ON {self.table_schema}.{self.table_name}
            FOR EACH ROW EXECUTE FUNCTION {self.table_schema}.{self.table_name}_audit();
            """
        )

    def create_sql_function(
        self,
        function_name: str,
        function_string: str,
        operation: str = "UPDATE",
        for_each: str = "ROW",
        include_trigger: bool = False,
    ) -> str:
        """
        Creates a SQL function and optionally a trigger for a PostgreSQL database.

        Args:
            function_name (str): The name of the SQL function to create.
            function_string (str): The body of the SQL function.
            operation (str, optional): The operation that will fire the trigger (e.g., "UPDATE", "INSERT"). Defaults to "UPDATE".
            for_each (str, optional): Specifies whether the trigger is for each row or statement. Defaults to "ROW".
            include_trigger (bool, optional): Whether to include a trigger creation statement. Defaults to False.

        Returns:
            str: The SQL string to create the function and optionally the trigger.
        """
        fnct_string = textwrap.dedent(
            f"CREATE OR REPLACE FUNCTION {self.schema_table_name}_{function_name}()\n"
            "RETURNS TRIGGER\n"
            "LANGUAGE plpgsql\n"
            "VOLATILE\n"
            "AS $BODY$\n"
            "BEGIN\n"
            f"  SET ROLE {sttngs.DB_NAME}_admin;\n"
            f"  {function_string}\n"
            "END;\n"
            "$BODY$;\n"
        )
        trggr_string = textwrap.dedent(
            f"CREATE OR REPLACE TRIGGER {self.table_name}_{function_name}_trigger\n"
            f"    AFTER {operation}\n"
            f"    ON {self.schema_table_name}\n"
            f"    FOR EACH {for_each}\n"
            f"    EXECUTE FUNCTION {self.schema_table_name}_{function_name}();\n"
        )
        sql_str = (
            f"{textwrap.dedent(fnct_string)}\n{textwrap.dedent(trggr_string)}"
            if include_trigger
            else fnct_string
        )
        return textwrap.dedent(sql_str)


class PropertyTool(TableTool):
    """
    PropertyTool is a subclass of TableTool that represents the schema for a property in a database table.
    It includes computed fields and methods to generate SQL statements for creating filter fields and their
    associated table types.

    Attributes:
        column (Column): The column associated with the property schema.
        model_config (ConfigDict): Configuration dictionary allowing arbitrary types.

    Methods:
        accessor() -> str:
            Computes and returns the accessor name for the column.

        data_type() -> str:
            Computes and returns the data type for the column.

        lookups() -> Lookup:
            Computes and returns the appropriate lookup type for the column based on its foreign keys
            and Python type.

        label() -> str:
            Computes and returns a human-readable label for the column by replacing underscores and
            "_id" suffixes with spaces and capitalizing words.

        create_filter_field_sql() -> str:
            Generates and returns the SQL statement to create a filter field and its associated table type.
            The SQL statement performs the following actions:
    """

    # accessor: str <- computed_field
    # data_type: str <- computed_field
    # lookups: Lookup <- computed_field
    # label: str <- computed_field

    column: Column

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def accessor(self) -> str:
        return self.column.name

    @computed_field
    def data_type(self) -> str:
        """Get the column type for a given column"""
        return f"quote_nullable(NEW.{self.accessor})"

    @computed_field
    def lookups(self) -> Lookup:
        if self.column.foreign_keys:
            return related_lookups
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

    @computed_field
    def label(self) -> str:
        return self.column.name.replace("_id", " ").replace("_", " ").title()

    def create_filter_field_sql(self) -> str:
        """
        Generates the SQL statement to create a filter field and its associated table type.

        This method constructs and returns a SQL statement that performs the following actions:
        1. Inserts a new filter field into the `un0.filterfield` table with the specified attributes.
           - If a conflict occurs on the combination of `label` and `graph_type`, the insertion is ignored.
        2. Inserts a relationship between the filter field and a table type into the `un0.filterfield_tabletype` table.
           - The relationship is defined by the `filterfield_id`, `tabletype_id`, and `direction`.
           - If a conflict occurs, the insertion is ignored.

        Returns:
            str: The SQL statement for creating the filter field and its associated table type.
        """
        return textwrap.dedent(
            f"""
            -- Create the filter field
            INSERT INTO un0.filterfield (
                accessor,
                label,
                data_type,
                graph_type,
                lookups
            )
            VALUES (
                '{self.accessor}',
                '{self.label}',
                '{self.column.type}',
                '{GraphType.PROPERTY.name}',
                ARRAY{self.lookups}::un0.lookup[]
            ) ON CONFLICT (label, graph_type) DO NOTHING;

            INSERT INTO un0.filterfield_tabletype (
                filterfield_id,
                tabletype_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.FROM.name}'
            FROM un0.filterfield f
            JOIN un0.tabletype t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.PROPERTY.name}'
            AND t.name = '{self.table_name}'
            AND t.schema = '{self.table_schema}'
            ON CONFLICT DO NOTHING;
            """
        )


class VertexTool(TableTool):
    """
    VertexTool is a subclass of TableTool that represents the schema for a vertex in a graph database.
    It includes various computed fields and methods to generate SQL statements for creating, updating,
    deleting, and truncating vertices and their associated edges and properties.

    Attributes:
        column (Column): The column associated with the vertex.
        lookups (list[Lookup]): A list of related lookups.
        table (Table): The table associated with the vertex.
        model_config (ConfigDict): Configuration for the model, allowing arbitrary types.

    Computed Fields:
        label (str): The label of the vertex, derived from the table name.
        accessor (str): The accessor for the vertex, derived from the table name.
        data_type (str): A SQL expression string to cast a column to its specified type.
        properties (list[PropertyTool] | None): A list of PropertyTool instances for each column in the table.
        edges (list[EdgeTool] | None): A list of EdgeTool objects representing the foreign key relationships of the table.

    Methods:
        create_sql() -> str:
        create_filter_field_sql() -> str:
        create_label_sql() -> str:
            Generates SQL code to create a vertex label and its corresponding index in the AgensGraph database.
        create_insert_function_and_trigger_sql() -> str:
            Generates SQL code to create a function and trigger for inserting a new vertex record.
        create_update_function_and_trigger_sql() -> str:
        create_delete_function_and_trigger_sql() -> str:
            Generates SQL code for creating a function and trigger to delete a vertex record.
        create_truncate_function_and_trigger_sql() -> str:
    """

    # label: str <- computed_field
    # accessor: str <- computed_field
    # data_type: str <- computed_field
    # properties: list[PropertyTool] | None <- computed_field
    # edges: list[EdgeTool] | None <- computed_field

    table: Table
    column: Column
    lookups: list[Lookup] = related_lookups

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def label(self) -> str:
        return convert_snake_to_capital_word(self.table.name)

    @computed_field
    def accessor(self) -> str:
        return self.table.name

    @computed_field
    def data_type(self) -> str:
        """
        Generates a string representing a SQL expression to cast a column to its specified type.

        Returns:
            str: A SQL expression string in the format "quote_nullable(NEW.<column_name>::<column_type>)".
        """
        return f"quote_nullable(NEW.{self.column.name}::{self.column.type})"

    @computed_field
    def properties(self) -> list["PropertyTool"] | None:
        """
        Generates a list of PropertyTool instances for each column in the table.

        Returns:
            list[PropertyTool] | None: A list of PropertyTool instances or None if no columns are present.
        """
        props = []
        for column in self.table.columns:
            props.append(PropertyTool(table=self.table, column=column))
        return props

    @computed_field
    def edges(self) -> list["EdgeTool"] | None:
        """
        Generates a list of EdgeTool objects representing the foreign key relationships
        of the table associated with this instance.

        Returns:
            list[EdgeTool] | None: A list of EdgeTool objects if foreign keys are present,
            otherwise None.
        """
        edges = []
        for fk in self.table.foreign_keys:
            edges.append(
                EdgeTool(
                    table=self.table,
                    to_column=fk.parent,
                    start_vertex=self,
                    end_vertex=VertexTool(
                        table=fk.column.table,
                        column=fk.parent,
                    ),
                )
            )
        return edges

    # Functions to generate sql statements

    def create_sql(self) -> str:
        """
        Generates a complete SQL script by combining various SQL components.

        This method constructs a SQL script by sequentially appending the results
        of several helper methods that generate specific parts of the SQL script.
        The final script includes SQL for creating labels, insert functions and
        triggers, update functions and triggers, delete functions and triggers,
        truncate functions and triggers, and filter fields.

        Returns:
            str: The complete SQL script as a single string.
        """
        sql = self.create_label_sql()
        sql += f"\n{self.create_insert_function_and_trigger_sql()}"
        sql += f"\n{self.create_update_function_and_trigger_sql()}"
        sql += f"\n{self.create_delete_function_and_trigger_sql()}"
        sql += f"\n{self.create_truncate_function_and_trigger_sql()}"
        sql += f"\n{self.create_filter_field_sql()}"
        return textwrap.dedent(sql)

    def create_filter_field_sql(self) -> str:
        """
        Generates the SQL statement to create a filter field and associate it with a table type.

        The SQL statement performs the following operations:
        1. Inserts a new filter field into the `un0.filterfield` table with the specified attributes.
           - If a conflict occurs on the combination of `label` and `graph_type`, the insertion is ignored.
        2. Inserts a new association between the filter field and a table type into the `un0.filterfield_tabletype` table.
           - The association includes the filter field ID, table type ID, and direction.
           - If a conflict occurs, the insertion is ignored.

        Returns:
            str: The generated SQL statement.
        """
        return textwrap.dedent(
            f"""
            -- Create the filter field
            INSERT INTO un0.filterfield (
                accessor,
                label,
                data_type,
                graph_type,
                lookups
            )
            VALUES (
                '{self.accessor}',
                '{self.label}',
                '{self.column.type}',
                '{GraphType.VERTEX.name}',
                ARRAY{self.lookups}::un0.lookup[]
            ) ON CONFLICT (label, graph_type) DO NOTHING;

            INSERT INTO un0.filterfield_tabletype (
                filterfield_id,
                tabletype_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.FROM.name}'
            FROM un0.filterfield f
            JOIN un0.tabletype t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.VERTEX.name}'
            AND t.name = '{self.table_name}'
            AND t.schema = '{self.table_schema}'
            ON CONFLICT DO NOTHING;
            """
        )

    def create_label_sql(self) -> str:
        """
        Generates SQL code to create a vertex label and its corresponding index
        in the AgensGraph database if it does not already exist.

        Returns:
            str: The SQL code to create the vertex label and index.
        """
        return textwrap.dedent(
            f"\n-- Create the vertex label and index\n"
            f"\nDO $$ \n"
            f"BEGIN\n"
            f"    IF NOT EXISTS (SELECT 1 FROM ag_catalog.ag_label\n"
            f"    WHERE name = '{self.label}') THEN\n"
            f"        PERFORM ag_catalog.create_vlabel('graph', '{self.label}');\n"
            f'        CREATE INDEX ON graph."{self.label}" (id);\n'
            f"    END IF;\n"
            f"END $$;\n"
        )

    def create_insert_function_and_trigger_sql(self) -> str:
        """
        Generates SQL code to create a function and trigger for inserting a new vertex record
        when a new relational table record is inserted.

        The function constructs the SQL statements required to:
        - Create a new vertex with the specified label and properties.
        - Create edges for the vertex if any are defined.

        Returns:
            str: The generated SQL code for the insert function and trigger.
        """
        prop_key_str = ""
        prop_val_str = ""
        edge_str = ""
        if self.edges:
            edge_str = "\n".join(
                [edge.create_insert_function_and_trigger_sql() for edge in self.edges]
            )

        if self.properties:
            prop_key_str = ", ".join(f"{prop.accessor}: %s" for prop in self.properties)
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        sql = textwrap.dedent(
            f"\n-- Create the insert vertex function and trigger\n"
            f"\nEXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$\n"
            f"    CREATE (v:{self.label} {{{prop_key_str}}})\n"
            f"$$) AS (a agtype);'{prop_val_str});\n"
            f"\n-- Create the edges for the vertex on insert\n"
            f"{edge_str}\n"
            f"RETURN NEW;\n"
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
        """
        Generates SQL code for creating an update function and trigger for a vertex record.

        This method constructs the SQL code necessary to update an existing vertex record
        in a graph database when its corresponding relational table record is updated. The
        generated SQL includes the necessary property updates and edge updates if they exist.

        Returns:
            str: The generated SQL code as a string.
        """
        prop_key_str = ""
        prop_val_str = ""
        edge_str = ""
        if self.edges:
            edge_str = "\n".join(
                [edge.create_update_function_and_trigger_sql() for edge in self.edges]
            )
        if self.properties:
            prop_key_str = "SET " + ", ".join(
                f"v.{prop.accessor} = %s" for prop in self.properties
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
        """
        Generates SQL code for creating a function and trigger to delete a vertex record
        from a graph database when its corresponding relational table record is deleted.

        Returns:
            str: The SQL code for creating the delete function and trigger.
        """
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
        """
        Generates SQL function and trigger for truncating a relation table.

        This method creates a SQL function and trigger that deletes all corresponding
        vertices for a relation table when the table is truncated. The generated SQL
        function uses the `cypher` command to match and detach delete vertices with
        the specified label.

        Returns:
            str: The SQL string to create the function and trigger.
        """
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


class EdgeTool(TableTool):
    """
    EdgeTool is a class that represents the schema for an edge in a graph database. It extends the TableTool class and includes additional attributes and methods specific to edges.
    Attributes:
        table (Table): The table associated with the edge.
        to_column (Column): The column representing the edge.
        start_vertex (VertexTool): The schema of the start vertex.
        end_vertex (VertexTool): The schema of the end vertex.
        lookups (list[Lookup]): A list of related lookups.
        in_vertex (bool): A flag indicating if the edge is in a vertex. Defaults to True.
        model_config (ConfigDict): Configuration for the model, allowing arbitrary types.
    Methods:
        label() -> str:
            Computes and returns the label for the edge.
        accessor() -> str:
            Computes and returns the accessor for the edge.
        properties() -> list["PropertyTool"]:
        create_sql() -> str:
        create_filter_field_sql() -> str:
            Returns the SQL to insert the edge as a filter field and creates the filterfield_tabletype records for the edge.
        create_label_sql() -> str:
        create_insert_function_and_trigger_sql() -> str:
            Generates an SQL string to create a function and trigger for inserting a relationship between two vertices in a graph database.
        create_update_function_and_trigger_sql() -> str:
        create_delete_function_and_trigger_sql() -> str:
        create_truncate_function_and_trigger_sql() -> str:
            Generates the SQL command to create a function and trigger for truncating relationships in a graph database.
    """

    # label: str <- computed_field
    # accessor: str <- computed_field
    # properties: list[PropertyTool] <- computed_field

    table: Table
    to_column: Column
    start_vertex: VertexTool
    end_vertex: VertexTool
    lookups: list[Lookup] = related_lookups
    in_vertex: bool = True

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def label(self) -> str:
        return self.to_column.info.get("edge")

    @computed_field
    def accessor(self) -> str:
        return self.to_column.name

    @computed_field
    def properties(self) -> list["PropertyTool"]:
        """
        Retrieves a list of PropertyTool objects for the current table.

        Returns:
            list[PropertyTool]: A list of PropertyTool objects representing
            the properties of the table's columns that are not foreign keys.
        """
        props = []
        if not self.in_vertex:
            for column in self.table.columns:
                if not column.foreign_keys:
                    props.append(PropertyTool(table=self.table, column=column))
        return props

    # Functions to generate sql statements

    def create_sql(self) -> str:
        """
        Generates the complete SQL string for creating various SQL functions and triggers.

        This method constructs SQL statements for creating label SQL, insert, update, delete,
        and truncate functions and their respective triggers. It also includes SQL for
        filtering fields. The generated SQL is dedented before being returned.

        Returns:
            str: The complete SQL string for creating the necessary functions and triggers.
        """
        sql = self.create_label_sql()
        sql += self.create_sql_function(
            "insert_edge",
            self.create_insert_function_and_trigger_sql(),
            operation="INSERT",
            for_each="ROW",
            include_trigger=True,
        )
        sql += self.create_sql_function(
            "update_edge",
            self.create_update_function_and_trigger_sql(),
            operation="UPDATE",
            for_each="ROW",
            include_trigger=True,
        )
        sql += self.create_sql_function(
            "delete_edge",
            self.create_delete_function_and_trigger_sql(),
            operation="DELETE",
            for_each="ROW",
            include_trigger=True,
        )
        sql += self.create_sql_function(
            "truncate_edge",
            self.create_truncate_function_and_trigger_sql(),
            operation="TRUNCATE",
            for_each="STATEMENT",
            include_trigger=True,
        )
        sql += self.create_filter_field_sql()
        return textwrap.dedent(sql)

    def create_filter_field_sql(self) -> str:
        """Returns the sql to insert the Edge as a filter field

        Additionally, it creates the filterfield_tabletype records for the edge
        for both the start and end vertices.
        """
        return textwrap.dedent(
            f"""
            -- Create the filter field
            INSERT INTO un0.filterfield (
                accessor,
                label,
                data_type,
                graph_type,
                lookups
            )
            VALUES (
                '{self.accessor}',
                '{self.label}',
                '{self.to_column.type}',
                '{GraphType.EDGE.name}',
                ARRAY{self.lookups}::un0.lookup[]
            ) ON CONFLICT (label, graph_type) DO NOTHING;

            INSERT INTO un0.filterfield_tabletype (
                filterfield_id,
                tabletype_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.FROM.name}'
            FROM un0.filterfield f
            JOIN un0.tabletype t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.EDGE.name}'
            AND t.name = '{self.table_name}'
            AND t.schema = '{self.table_schema}'
            ON CONFLICT DO NOTHING;
    
            INSERT INTO un0.filterfield_tabletype (
                filterfield_id,
                tabletype_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.TO.name}'
            FROM un0.filterfield f
            JOIN un0.tabletype t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.EDGE.name}'
            AND t.name = '{self.end_vertex.table.name}'
            AND t.schema = '{self.end_vertex.table.schema}'
            ON CONFLICT DO NOTHING;
            """
        )

    def create_label_sql(self) -> str:
        """
        Generates a SQL statement to create a label in the AgensGraph database if it does not already exist.

        Returns:
            str: A SQL statement that checks for the existence of a label in the ag_catalog.ag_label table.
                 If the label does not exist, it creates the label and an index on the 'graph' schema.
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
        """
        Generates an SQL string to create a function and trigger for inserting
        a relationship between two vertices in a graph database.

        The generated SQL uses the `cypher` function to match the start and end
        vertices by their IDs and creates a relationship between them with the
        specified label and properties.

        Returns:
            str: The generated SQL string.
        """
        prop_key_str = ""
        prop_val_str = ""
        if self.properties:
            prop_key_str = ", ".join(f"{prop.accessor}: %s" for prop in self.properties)
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        sql = f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                CREATE (v)-[e:{self.label} {{{prop_key_str}}}] ->(w)
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type}{prop_val_str});
            """
        # if not self.in_vertex:
        #    sql += "\nRETURN NEW;"
        return textwrap.dedent(sql)

    def create_update_function_and_trigger_sql(self) -> str:
        """
        Generates the SQL string for creating an update function and trigger in a graph database.

        This function constructs a SQL query that:
        - Matches a start vertex and an end vertex based on their labels and IDs.
        - Deletes an existing relationship between the vertices.
        - Creates a new relationship between the vertices with updated properties.

        Returns:
            str: The formatted SQL string for the update function and trigger.
        """

        prop_key_str = ""
        prop_val_str = ""
        if self.properties:
            prop_key_str = "SET " + ", ".join(
                f"v.{prop.accessor} = %s" for prop in self.properties
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
        Generates the SQL string for creating a delete function and trigger.

        This function constructs an SQL command that uses the `cypher` function to
        delete a relationship between two vertices in a graph database. The vertices
        and the relationship are specified by the attributes of the class instance.

        Returns:
            str: The formatted SQL string for deleting the specified relationship.
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
        Generates the SQL command to create a function and trigger for truncating
        relationships in a graph database.

        This method constructs a SQL string that uses the `cypher` function to
        match and delete a relationship between two vertices in a graph. The
        vertices and relationship are specified by the `start_vertex`,
        `end_vertex`, and `label` attributes of the class instance.

        Returns:
            str: The formatted SQL command string.
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


class TableTool(BaseModel):
    """
    TableTool is a Pydantic model that represents the schema of a database table. It includes various computed fields and methods to generate SQL statements for configuring the table, enabling auditing, and creating triggers.

    Attributes:
        table (Table): The SQLAlchemy Table object representing the database table.
        model_config (dict): Configuration for the Pydantic model, allowing arbitrary types.

    Computed Fields:
        table_schema (str): The schema of the table.
        table_name (str): The name of the table.
        schema_table_name (str): The full name of the table including schema.
        rls_policy (str): The row-level security policy for the table.
        graph (bool): Indicates if the table is part of a graph.
        vertex (VertexTool): The vertex schema if the table is a vertex.
        edges (list[EdgeTool] | None): The edges schema if the table has foreign keys.
        properties (list[PropertyTool] | None): The properties schema for the table columns.

    Methods:
        configuration_sql() -> str: Generates SQL statements for configuring the table.
        create_tabletype_record() -> str: Generates SQL to create a table type record.
        enable_rls() -> str: Generates SQL to enable row-level security for the table.
        create_set_owner_and_modified_trigger() -> str: Generates SQL to create a trigger for setting owner and modified fields.
        create_history_table_triggercreate_set_owner_and_modified_trigger() -> str: Generates SQL to create a trigger for setting owner and modified fields.
        create_validate_delete_trigger() -> str: Generates SQL to create a trigger for validating deletes.
        change_table_owner_and_set_privileges() -> str: Generates SQL to change table owner and set privileges.
        enable_auditing() -> str: Generates SQL to enable auditing for the table.
        create_history_table() -> str: Generates SQL to create a history table for auditing.
        create_history_table_trigger() -> str: Generates SQL to create a trigger for the history table.
        create_sql_function(function_name: str, function_string: str, operation: str = "UPDATE", for_each: str = "ROW", include_trigger: bool = False) -> str: Creates a SQL function and optionally a trigger for a PostgreSQL database.
    """

    # filter_set: "FilterSetSchema" = None
    # table_name: str <- computed_field
    # table_schema: str <- computed_field
    # schema_table_name: str <- computed_field
    # rls_policy: str <- computed_field
    # in_graph: bool <- computed_field
    # vertex: VertexTool <- computed_field
    # edges: EdgeTool <- computed_field
    # properties: PropertyTool <- computed_field

    table: Table

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def table_schema(self) -> str:
        return self.table.schema

    @computed_field
    def table_name(self) -> str:
        return self.table.name

    @computed_field
    def schema_table_name(self) -> str:
        return f"{self.table_schema}.{self.table_name}"

    @computed_field
    def rls_policy(self) -> str:
        return self.table.info.get("rls_policy", "UserGroup")

    @computed_field
    def graph(self) -> bool:
        return self.table.info.get("in_graph", True)

    @computed_field
    def vertex(self) -> bool:
        """
        Determines if the table is a vertex and returns a VertexTool instance if true.

        Returns:
            VertexTool: An instance of VertexTool if the table is a vertex.
            bool: False if the table is not a vertex.
        """
        if self.table.info.get("vertex", True) is not False:
            return VertexTool(
                table=self.table, column=self.table.primary_key.columns[0]
            )

    @computed_field
    def edges(self) -> list["EdgeTool"] | None:
        """
        Generates a list of EdgeTool objects representing the edges in the database schema.

        This method iterates over the foreign keys of the table and their corresponding columns to create
        EdgeTool instances. Each EdgeTool represents a relationship between two vertices (start and end)
        in the schema.

        Returns:
            list[EdgeTool] | None: A list of EdgeTool objects if any edges are found, otherwise None.
        """
        edges = []
        for fk in self.table.foreign_keys:
            for column in self.table.columns:
                if fk.parent.name == column.name:
                    continue
                for _fk in column.foreign_keys:
                    edges.append(
                        EdgeTool(
                            table=self.table,
                            to_column=column,
                            start_vertex=VertexTool(
                                table=self.table,
                                column=fk.parent,
                            ),
                            end_vertex=VertexTool(
                                table=fk.column.table,
                                column=fk.column,
                            ),
                        )
                    )
        return edges

    @computed_field
    def properties(self) -> list["PropertyTool"] | None:
        """
        Retrieves a list of PropertyTool objects for each column in the table.

        Returns:
            list[PropertyTool] | None: A list of PropertyTool objects representing
            the properties of each column in the table, or None if there are no columns.
        """
        props = []
        for column in self.table.columns:
            props.append(PropertyTool(table=self.table, column=column))
        return props

    # Functions to generate sql statements
    def configuration_sql(self) -> str:
        """
        Generates the SQL configuration string for setting up the database table.

        This method constructs a SQL string that includes:
        - Setting the role to the database admin.
        - Changing the table owner and setting privileges.
        - Creating a table type record.
        - Optionally creating triggers for setting owner and modified timestamps, and validating deletes if the table has an "owner_id" column.
        - Enabling auditing based on the table's audit type:
            - "basic": Enables default auditing.
            - "history": Creates a history table and trigger for auditing changes.
        - Creating vertex and edge triggers if applicable.
        - Creating filter field SQL for properties.

        Returns:
            str: The complete SQL configuration string.
        """
        sql = textwrap.dedent(
            f"SET ROLE {sttngs.DB_NAME}_admin;"
            f"\n{self.change_table_owner_and_set_privileges()}"
            f"\n{self.create_tabletype_record()}"
        )

        if "owner_id" in self.table.columns:
            sql += f"\n{textwrap.dedent(self.create_set_owner_and_modified_trigger())}"
            sql += f"\n{textwrap.dedent(self.create_validate_delete_trigger())}"

        # Enables auditing for the table if the audit_type is not set to None in the tables info dictionary.
        # If the audit_type is set to "history", then the history table and trigger are created for the table
        #    - A duplicate of the table is created as audit.[table_schema]_[table_name]
        #    - The trigger is created to insert a duplicate record into the history table after insert or update
        #    - A function is created to restore a record from the history table to the actual table
        # If the audit_type is set to None, then no un0 auditing occurs.
        # Otherwise, the audit trigger is created as a default:
        #    - all changes will be audited in the audit.record_version table, using supabase_audit.
        audit_type = self.table.info.get("audit", "basic")
        if audit_type == "basic":
            sql += f"\n{textwrap.dedent(self.enable_auditing())}"
        elif audit_type == "history":
            sql += f"\n{textwrap.dedent(self.create_history_table())}"
            sql += f"\n{textwrap.dedent(self.create_history_table_trigger())}"

        # Create the vertex and edge triggers
        if self.vertex:
            sql += f"\n{textwrap.dedent(self.vertex.create_sql())}"
        else:
            for edge in self.edges:
                sql += f"\n{textwrap.dedent(edge.create_sql())}"
        for prop in self.properties:
            sql += f"\n{textwrap.dedent(prop.create_filter_field_sql())}"

        # if self.table.info.get("rls_policy", None) is not None:
        #    sql += f"\n{textwrap.dedent(self.enable_rls())}"
        #
        return sql

    def create_tabletype_record(self) -> str:
        """
        Generates an SQL statement to insert a record into the `un0.tabletype` table.

        This method creates a SQL INSERT statement that adds a new record to the
        `un0.tabletype` table with the schema and name provided by the instance's
        `table_schema` and `table_name` attributes.

        Returns:
            str: A formatted SQL INSERT statement as a string.
        """
        return textwrap.dedent(
            f"""
            -- Create the tabletype record
            INSERT INTO un0.tabletype (schema, name)
            VALUES ('{self.table_schema}', '{self.table_name}');
            """
        )

    def enable_rls(self) -> str:
        """
        Generates SQL statements to enable and enforce Row Level Security (RLS)
        on a specified table.

        Returns:
            str: A string containing the SQL statements to enable and force RLS
                 for the table.
        """
        return textwrap.dedent(
            f"""
            -- Enable RLS for the table
            ALTER TABLE {self.schema_table_name} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {self.schema_table_name} FORCE ROW LEVEL SECURITY;
            """
        )

    def create_set_owner_and_modified_trigger(self) -> str:
        """
        Generates a SQL trigger creation statement for setting the owner and
        modified timestamp on a specified table.

        This method creates a trigger named 'set_owner_and_modified_trigger'
        that will be executed before any INSERT or UPDATE operation on the
        table specified by `self.schema_table_name`. The trigger will call
        the function `un0.set_owner_and_modified()` to set the owner and
        modified timestamp.

        Returns:
            str: A SQL statement for creating the trigger.
        """
        return textwrap.dedent(
            f"""
            CREATE TRIGGER set_owner_and_modified_trigger
            BEFORE INSERT OR UPDATE ON {self.schema_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION un0.set_owner_and_modified();
            """
        )

    def create_history_table_triggercreate_set_owner_and_modified_trigger(self) -> str:
        """
        Generates a SQL trigger creation statement for setting the owner and modified timestamp.

        This method returns a SQL statement that creates a trigger named
        `set_owner_and_modified_trigger`. The trigger is executed before
        any INSERT or UPDATE operation on the specified table, and it
        calls the `un0.set_owner_and_modified()` function.

        Returns:
            str: A SQL statement for creating the trigger.
        """
        return textwrap.dedent(
            f"""
            CREATE TRIGGER set_owner_and_modified_trigger
            BEFORE INSERT OR UPDATE ON {self.schema_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION un0.set_owner_and_modified();
            """
        )

    def create_validate_delete_trigger(self) -> str:
        """
        Generates a SQL trigger creation statement for validating deletions.

        This method creates a SQL trigger named `validate_delete_trigger` that is
        executed before a delete operation on the specified table. The trigger
        calls the `un0.validate_delete()` function to perform validation.

        Returns:
            str: A SQL statement for creating the `validate_delete_trigger`.
        """
        return textwrap.dedent(
            f"""
            CREATE TRIGGER validate_delete_trigger 
            BEFORE DELETE ON {self.schema_table_name}
            FOR EACH ROW
            EXECUTE FUNCTION un0.validate_delete();
            """
        )

    def change_table_owner_and_set_privileges(self) -> str:
        """
        Generates a SQL command to change the owner of a table and set privileges.

        The generated SQL command will:
        - Change the owner of the table to the admin user of the database.
        - Grant SELECT privileges to the reader and writer roles.
        - Grant INSERT, UPDATE, and DELETE privileges to the writer role.

        Returns:
            str: A formatted SQL command string.
        """
        return textwrap.dedent(
            f"""
            ALTER TABLE {self.schema_table_name} OWNER TO {sttngs.DB_NAME}_admin;
            GRANT SELECT ON {self.schema_table_name} TO
                {sttngs.DB_NAME}_reader,
                {sttngs.DB_NAME}_writer;
            GRANT INSERT, UPDATE, DELETE ON {self.schema_table_name} TO
                {sttngs.DB_NAME}_writer;
            """
        )

    def enable_auditing(self) -> str:
        """
        Generates a SQL query to enable auditing for the specified table.

        Returns:
            str: A SQL query string that enables auditing for the table.
        """
        return textwrap.dedent(
            f"""
            -- Enable auditing for the table
            SELECT audit.enable_tracking('{self.schema_table_name}'::regclass);
            """
        )

    def create_history_table(self) -> str:
        """
        Creates a SQL statement to generate a history table for auditing purposes.

        The history table will be created in the 'audit' schema and will have the same structure
        as the original table, but without any data. Additionally, it will have an auto-incrementing
        primary key column and two indexes: one on the primary key and another on the combination
        of 'id' and 'modified_at' columns.

        Returns:
            str: A SQL statement to create the history table.
        """
        return textwrap.dedent(
            f"""
            CREATE TABLE audit.{self.table_schema}_{self.table_name}
            AS (SELECT * FROM {self.table_schema}.{self.table_name})
            WITH NO DATA;

            ALTER TABLE audit.{self.table_schema}_{self.table_name}
            ADD COLUMN pk INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;

            CREATE INDEX {self.table_schema}_{self.table_name}_pk_idx
            ON audit.{self.table_schema}_{self.table_name} (pk);

            CREATE INDEX {self.table_schema}_{self.table_name}_id_modified_at_idx
            ON audit.{self.table_schema}_{self.table_name} (id, modified_at);
            """
        )

    def create_history_table_trigger(self) -> str:
        """
        Generates a SQL trigger function and trigger for auditing changes to a table.

        This method creates a PostgreSQL function and trigger that logs changes to a specified table
        into an audit table. The function and trigger are created within the same schema as the target table.

        Returns:
            str: A string containing the SQL statements to create the audit function and trigger.
        """
        return textwrap.dedent(
            f"""
            CREATE OR REPLACE FUNCTION {self.table_schema}.{self.table_name}_audit()
            RETURNS TRIGGER
            LANGUAGE plpgsql
            SECURITY DEFINER
            AS $$
            BEGIN
                INSERT INTO audit.{self.table_schema}_{self.table_name}
                SELECT *
                FROM {self.table_schema}.{self.table_name}
                WHERE id = NEW.id;
                RETURN NEW;
            END;
            $$;

            CREATE OR REPLACE TRIGGER {self.table_name}_audit_trigger
            AFTER INSERT OR UPDATE ON {self.table_schema}.{self.table_name}
            FOR EACH ROW EXECUTE FUNCTION {self.table_schema}.{self.table_name}_audit();
            """
        )

    def create_sql_function(
        self,
        function_name: str,
        function_string: str,
        operation: str = "UPDATE",
        for_each: str = "ROW",
        include_trigger: bool = False,
    ) -> str:
        """
        Creates a SQL function and optionally a trigger for a PostgreSQL database.

        Args:
            function_name (str): The name of the SQL function to create.
            function_string (str): The body of the SQL function.
            operation (str, optional): The operation that will fire the trigger (e.g., "UPDATE", "INSERT"). Defaults to "UPDATE".
            for_each (str, optional): Specifies whether the trigger is for each row or statement. Defaults to "ROW".
            include_trigger (bool, optional): Whether to include a trigger creation statement. Defaults to False.

        Returns:
            str: The SQL string to create the function and optionally the trigger.
        """
        fnct_string = textwrap.dedent(
            f"CREATE OR REPLACE FUNCTION {self.schema_table_name}_{function_name}()\n"
            "RETURNS TRIGGER\n"
            "LANGUAGE plpgsql\n"
            "VOLATILE\n"
            "AS $BODY$\n"
            "BEGIN\n"
            f"  SET ROLE {sttngs.DB_NAME}_admin;\n"
            f"  {function_string}\n"
            "END;\n"
            "$BODY$;\n"
        )
        trggr_string = textwrap.dedent(
            f"CREATE OR REPLACE TRIGGER {self.table_name}_{function_name}_trigger\n"
            f"    AFTER {operation}\n"
            f"    ON {self.schema_table_name}\n"
            f"    FOR EACH {for_each}\n"
            f"    EXECUTE FUNCTION {self.schema_table_name}_{function_name}();\n"
        )
        sql_str = (
            f"{textwrap.dedent(fnct_string)}\n{textwrap.dedent(trggr_string)}"
            if include_trigger
            else fnct_string
        )
        return textwrap.dedent(sql_str)


class PropertyTool(TableTool):
    """
    PropertyTool is a subclass of TableTool that represents the schema for a property in a database table.
    It includes computed fields and methods to generate SQL statements for creating filter fields and their
    associated table types.

    Attributes:
        column (Column): The column associated with the property schema.
        model_config (dict): Configuration dictionary allowing arbitrary types.

    Methods:
        accessor() -> str:
            Computes and returns the accessor name for the column.

        data_type() -> str:
            Computes and returns the data type for the column.

        lookups() -> Lookup:
            Computes and returns the appropriate lookup type for the column based on its foreign keys
            and Python type.

        label() -> str:
            Computes and returns a human-readable label for the column by replacing underscores and
            "_id" suffixes with spaces and capitalizing words.

        create_filter_field_sql() -> str:
            Generates and returns the SQL statement to create a filter field and its associated table type.
            The SQL statement performs the following actions:
    """

    # accessor: str <- computed_field
    # data_type: str <- computed_field
    # lookups: Lookup <- computed_field
    # label: str <- computed_field

    column: Column

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def accessor(self) -> str:
        return self.column.name

    @computed_field
    def data_type(self) -> str:
        """Get the column type for a given column"""
        return f"quote_nullable(NEW.{self.accessor})"

    @computed_field
    def lookups(self) -> Lookup:
        if self.column.foreign_keys:
            return related_lookups
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

    @computed_field
    def label(self) -> str:
        return self.column.name.replace("_id", " ").replace("_", " ").title()

    def create_filter_field_sql(self) -> str:
        """
        Generates the SQL statement to create a filter field and its associated table type.

        This method constructs and returns a SQL statement that performs the following actions:
        1. Inserts a new filter field into the `un0.filterfield` table with the specified attributes.
           - If a conflict occurs on the combination of `label` and `graph_type`, the insertion is ignored.
        2. Inserts a relationship between the filter field and a table type into the `un0.filterfield_tabletype` table.
           - The relationship is defined by the `filterfield_id`, `tabletype_id`, and `direction`.
           - If a conflict occurs, the insertion is ignored.

        Returns:
            str: The SQL statement for creating the filter field and its associated table type.
        """
        return textwrap.dedent(
            f"""
            -- Create the filter field
            INSERT INTO un0.filterfield (
                accessor,
                label,
                data_type,
                graph_type,
                lookups
            )
            VALUES (
                '{self.accessor}',
                '{self.label}',
                '{self.column.type}',
                '{GraphType.PROPERTY.name}',
                ARRAY{self.lookups}::un0.lookup[]
            ) ON CONFLICT (label, graph_type) DO NOTHING;

            INSERT INTO un0.filterfield_tabletype (
                filterfield_id,
                tabletype_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.FROM.name}'
            FROM un0.filterfield f
            JOIN un0.tabletype t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.PROPERTY.name}'
            AND t.name = '{self.table_name}'
            AND t.schema = '{self.table_schema}'
            ON CONFLICT DO NOTHING;
            """
        )


class VertexTool(TableTool):
    """
    VertexTool is a subclass of TableTool that represents the schema for a vertex in a graph database.
    It includes various computed fields and methods to generate SQL statements for creating, updating,
    deleting, and truncating vertices and their associated edges and properties.

    Attributes:
        column (Column): The column associated with the vertex.
        lookups (list[Lookup]): A list of related lookups.
        table (Table): The table associated with the vertex.
        model_config (dict): Configuration for the model, allowing arbitrary types.

    Computed Fields:
        label (str): The label of the vertex, derived from the table name.
        accessor (str): The accessor for the vertex, derived from the table name.
        data_type (str): A SQL expression string to cast a column to its specified type.
        properties (list[PropertyTool] | None): A list of PropertyTool instances for each column in the table.
        edges (list[EdgeTool] | None): A list of EdgeTool objects representing the foreign key relationships of the table.

    Methods:
        create_sql() -> str:
        create_filter_field_sql() -> str:
        create_label_sql() -> str:
            Generates SQL code to create a vertex label and its corresponding index in the AgensGraph database.
        create_insert_function_and_trigger_sql() -> str:
            Generates SQL code to create a function and trigger for inserting a new vertex record.
        create_update_function_and_trigger_sql() -> str:
        create_delete_function_and_trigger_sql() -> str:
            Generates SQL code for creating a function and trigger to delete a vertex record.
        create_truncate_function_and_trigger_sql() -> str:
    """

    # label: str <- computed_field
    # accessor: str <- computed_field
    # data_type: str <- computed_field
    # properties: list[PropertyTool] | None <- computed_field
    # edges: list[EdgeTool] | None <- computed_field

    table: Table
    column: Column
    lookups: list[Lookup] = related_lookups

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def label(self) -> str:
        return convert_snake_to_capital_word(self.table.name)

    @computed_field
    def accessor(self) -> str:
        return self.table.name

    @computed_field
    def data_type(self) -> str:
        """
        Generates a string representing a SQL expression to cast a column to its specified type.

        Returns:
            str: A SQL expression string in the format "quote_nullable(NEW.<column_name>::<column_type>)".
        """
        return f"quote_nullable(NEW.{self.column.name}::{self.column.type})"

    @computed_field
    def properties(self) -> list["PropertyTool"] | None:
        """
        Generates a list of PropertyTool instances for each column in the table.

        Returns:
            list[PropertyTool] | None: A list of PropertyTool instances or None if no columns are present.
        """
        props = []
        for column in self.table.columns:
            props.append(PropertyTool(table=self.table, column=column))
        return props

    @computed_field
    def edges(self) -> list["EdgeTool"] | None:
        """
        Generates a list of EdgeTool objects representing the foreign key relationships
        of the table associated with this instance.

        Returns:
            list[EdgeTool] | None: A list of EdgeTool objects if foreign keys are present,
            otherwise None.
        """
        edges = []
        for fk in self.table.foreign_keys:
            edges.append(
                EdgeTool(
                    table=self.table,
                    to_column=fk.parent,
                    start_vertex=self,
                    end_vertex=VertexTool(
                        table=fk.column.table,
                        column=fk.parent,
                    ),
                )
            )
        return edges

    # Functions to generate sql statements

    def create_sql(self) -> str:
        """
        Generates a complete SQL script by combining various SQL components.

        This method constructs a SQL script by sequentially appending the results
        of several helper methods that generate specific parts of the SQL script.
        The final script includes SQL for creating labels, insert functions and
        triggers, update functions and triggers, delete functions and triggers,
        truncate functions and triggers, and filter fields.

        Returns:
            str: The complete SQL script as a single string.
        """
        sql = self.create_label_sql()
        sql += f"\n{self.create_insert_function_and_trigger_sql()}"
        sql += f"\n{self.create_update_function_and_trigger_sql()}"
        sql += f"\n{self.create_delete_function_and_trigger_sql()}"
        sql += f"\n{self.create_truncate_function_and_trigger_sql()}"
        sql += f"\n{self.create_filter_field_sql()}"
        return textwrap.dedent(sql)

    def create_filter_field_sql(self) -> str:
        """
        Generates the SQL statement to create a filter field and associate it with a table type.

        The SQL statement performs the following operations:
        1. Inserts a new filter field into the `un0.filterfield` table with the specified attributes.
           - If a conflict occurs on the combination of `label` and `graph_type`, the insertion is ignored.
        2. Inserts a new association between the filter field and a table type into the `un0.filterfield_tabletype` table.
           - The association includes the filter field ID, table type ID, and direction.
           - If a conflict occurs, the insertion is ignored.

        Returns:
            str: The generated SQL statement.
        """
        return textwrap.dedent(
            f"""
            -- Create the filter field
            INSERT INTO un0.filterfield (
                accessor,
                label,
                data_type,
                graph_type,
                lookups
            )
            VALUES (
                '{self.accessor}',
                '{self.label}',
                '{self.column.type}',
                '{GraphType.VERTEX.name}',
                ARRAY{self.lookups}::un0.lookup[]
            ) ON CONFLICT (label, graph_type) DO NOTHING;

            INSERT INTO un0.filterfield_tabletype (
                filterfield_id,
                tabletype_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.FROM.name}'
            FROM un0.filterfield f
            JOIN un0.tabletype t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.VERTEX.name}'
            AND t.name = '{self.table_name}'
            AND t.schema = '{self.table_schema}'
            ON CONFLICT DO NOTHING;
            """
        )

    def create_label_sql(self) -> str:
        """
        Generates SQL code to create a vertex label and its corresponding index
        in the AgensGraph database if it does not already exist.

        Returns:
            str: The SQL code to create the vertex label and index.
        """
        return textwrap.dedent(
            f"\n-- Create the vertex label and index\n"
            f"\nDO $$ \n"
            f"BEGIN\n"
            f"    IF NOT EXISTS (SELECT 1 FROM ag_catalog.ag_label\n"
            f"    WHERE name = '{self.label}') THEN\n"
            f"        PERFORM ag_catalog.create_vlabel('graph', '{self.label}');\n"
            f'        CREATE INDEX ON graph."{self.label}" (id);\n'
            f"    END IF;\n"
            f"END $$;\n"
        )

    def create_insert_function_and_trigger_sql(self) -> str:
        """
        Generates SQL code to create a function and trigger for inserting a new vertex record
        when a new relational table record is inserted.

        The function constructs the SQL statements required to:
        - Create a new vertex with the specified label and properties.
        - Create edges for the vertex if any are defined.

        Returns:
            str: The generated SQL code for the insert function and trigger.
        """
        prop_key_str = ""
        prop_val_str = ""
        edge_str = ""
        if self.edges:
            edge_str = "\n".join(
                [edge.create_insert_function_and_trigger_sql() for edge in self.edges]
            )

        if self.properties:
            prop_key_str = ", ".join(f"{prop.accessor}: %s" for prop in self.properties)
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        sql = textwrap.dedent(
            f"\n-- Create the insert vertex function and trigger\n"
            f"\nEXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$\n"
            f"    CREATE (v:{self.label} {{{prop_key_str}}})\n"
            f"$$) AS (a agtype);'{prop_val_str});\n"
            f"\n-- Create the edges for the vertex on insert\n"
            f"{edge_str}\n"
            f"RETURN NEW;\n"
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
        """
        Generates SQL code for creating an update function and trigger for a vertex record.

        This method constructs the SQL code necessary to update an existing vertex record
        in a graph database when its corresponding relational table record is updated. The
        generated SQL includes the necessary property updates and edge updates if they exist.

        Returns:
            str: The generated SQL code as a string.
        """
        prop_key_str = ""
        prop_val_str = ""
        edge_str = ""
        if self.edges:
            edge_str = "\n".join(
                [edge.create_update_function_and_trigger_sql() for edge in self.edges]
            )
        if self.properties:
            prop_key_str = "SET " + ", ".join(
                f"v.{prop.accessor} = %s" for prop in self.properties
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
        """
        Generates SQL code for creating a function and trigger to delete a vertex record
        from a graph database when its corresponding relational table record is deleted.

        Returns:
            str: The SQL code for creating the delete function and trigger.
        """
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
        """
        Generates SQL function and trigger for truncating a relation table.

        This method creates a SQL function and trigger that deletes all corresponding
        vertices for a relation table when the table is truncated. The generated SQL
        function uses the `cypher` command to match and detach delete vertices with
        the specified label.

        Returns:
            str: The SQL string to create the function and trigger.
        """
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


class EdgeTool(TableTool):
    """
    EdgeTool is a class that represents the schema for an edge in a graph database. It extends the TableTool class and includes additional attributes and methods specific to edges.
    Attributes:
        table (Table): The table associated with the edge.
        to_column (Column): The column representing the edge.
        start_vertex (VertexTool): The schema of the start vertex.
        end_vertex (VertexTool): The schema of the end vertex.
        lookups (list[Lookup]): A list of related lookups.
        in_vertex (bool): A flag indicating if the edge is in a vertex. Defaults to True.
        model_config (dict): Configuration for the model, allowing arbitrary types.
    Methods:
        label() -> str:
            Computes and returns the label for the edge.
        accessor() -> str:
            Computes and returns the accessor for the edge.
        properties() -> list["PropertyTool"]:
        create_sql() -> str:
        create_filter_field_sql() -> str:
            Returns the SQL to insert the edge as a filter field and creates the filterfield_tabletype records for the edge.
        create_label_sql() -> str:
        create_insert_function_and_trigger_sql() -> str:
            Generates an SQL string to create a function and trigger for inserting a relationship between two vertices in a graph database.
        create_update_function_and_trigger_sql() -> str:
        create_delete_function_and_trigger_sql() -> str:
        create_truncate_function_and_trigger_sql() -> str:
            Generates the SQL command to create a function and trigger for truncating relationships in a graph database.
    """

    # label: str <- computed_field
    # accessor: str <- computed_field
    # properties: list[PropertyTool] <- computed_field

    table: Table
    to_column: Column
    start_vertex: VertexTool
    end_vertex: VertexTool
    lookups: list[Lookup] = related_lookups
    in_vertex: bool = True

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def label(self) -> str:
        return self.to_column.info.get("edge")

    @computed_field
    def accessor(self) -> str:
        return self.to_column.name

    @computed_field
    def properties(self) -> list["PropertyTool"]:
        """
        Retrieves a list of PropertyTool objects for the current table.

        Returns:
            list[PropertyTool]: A list of PropertyTool objects representing
            the properties of the table's columns that are not foreign keys.
        """
        props = []
        if not self.in_vertex:
            for column in self.table.columns:
                if not column.foreign_keys:
                    props.append(PropertyTool(table=self.table, column=column))
        return props

    # Functions to generate sql statements

    def create_sql(self) -> str:
        """
        Generates the complete SQL string for creating various SQL functions and triggers.

        This method constructs SQL statements for creating label SQL, insert, update, delete,
        and truncate functions and their respective triggers. It also includes SQL for
        filtering fields. The generated SQL is dedented before being returned.

        Returns:
            str: The complete SQL string for creating the necessary functions and triggers.
        """
        sql = self.create_label_sql()
        sql += self.create_sql_function(
            "insert_edge",
            self.create_insert_function_and_trigger_sql(),
            operation="INSERT",
            for_each="ROW",
            include_trigger=True,
        )
        sql += self.create_sql_function(
            "update_edge",
            self.create_update_function_and_trigger_sql(),
            operation="UPDATE",
            for_each="ROW",
            include_trigger=True,
        )
        sql += self.create_sql_function(
            "delete_edge",
            self.create_delete_function_and_trigger_sql(),
            operation="DELETE",
            for_each="ROW",
            include_trigger=True,
        )
        sql += self.create_sql_function(
            "truncate_edge",
            self.create_truncate_function_and_trigger_sql(),
            operation="TRUNCATE",
            for_each="STATEMENT",
            include_trigger=True,
        )
        sql += self.create_filter_field_sql()
        return textwrap.dedent(sql)

    def create_filter_field_sql(self) -> str:
        """Returns the sql to insert the Edge as a filter field

        Additionally, it creates the filterfield_tabletype records for the edge
        for both the start and end vertices.
        """
        return textwrap.dedent(
            f"""
            -- Create the filter field
            INSERT INTO un0.filterfield (
                accessor,
                label,
                data_type,
                graph_type,
                lookups
            )
            VALUES (
                '{self.accessor}',
                '{self.label}',
                '{self.to_column.type}',
                '{GraphType.EDGE.name}',
                ARRAY{self.lookups}::un0.lookup[]
            ) ON CONFLICT (label, graph_type) DO NOTHING;

            INSERT INTO un0.filterfield_tabletype (
                filterfield_id,
                tabletype_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.FROM.name}'
            FROM un0.filterfield f
            JOIN un0.tabletype t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.EDGE.name}'
            AND t.name = '{self.table_name}'
            AND t.schema = '{self.table_schema}'
            ON CONFLICT DO NOTHING;
    
            INSERT INTO un0.filterfield_tabletype (
                filterfield_id,
                tabletype_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.TO.name}'
            FROM un0.filterfield f
            JOIN un0.tabletype t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.EDGE.name}'
            AND t.name = '{self.end_vertex.table.name}'
            AND t.schema = '{self.end_vertex.table.schema}'
            ON CONFLICT DO NOTHING;
            """
        )

    def create_label_sql(self) -> str:
        """
        Generates a SQL statement to create a label in the AgensGraph database if it does not already exist.

        Returns:
            str: A SQL statement that checks for the existence of a label in the ag_catalog.ag_label table.
                 If the label does not exist, it creates the label and an index on the 'graph' schema.
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
        """
        Generates an SQL string to create a function and trigger for inserting
        a relationship between two vertices in a graph database.

        The generated SQL uses the `cypher` function to match the start and end
        vertices by their IDs and creates a relationship between them with the
        specified label and properties.

        Returns:
            str: The generated SQL string.
        """
        prop_key_str = ""
        prop_val_str = ""
        if self.properties:
            prop_key_str = ", ".join(f"{prop.accessor}: %s" for prop in self.properties)
            prop_val_str = ", " + ", ".join(
                [prop.data_type for prop in self.properties]
            )
        sql = f"""
            EXECUTE FORMAT('SELECT * FROM cypher(''graph'', $$
                MATCH (v:{self.start_vertex.label} {{id: %s}})
                MATCH (w:{self.end_vertex.label} {{id: %s}})
                CREATE (v)-[e:{self.label} {{{prop_key_str}}}] ->(w)
            $$) AS (e agtype);', {self.start_vertex.data_type}, {self.end_vertex.data_type}{prop_val_str});
            """
        # if not self.in_vertex:
        #    sql += "\nRETURN NEW;"
        return textwrap.dedent(sql)

    def create_update_function_and_trigger_sql(self) -> str:
        """
        Generates the SQL string for creating an update function and trigger in a graph database.

        This function constructs a SQL query that:
        - Matches a start vertex and an end vertex based on their labels and IDs.
        - Deletes an existing relationship between the vertices.
        - Creates a new relationship between the vertices with updated properties.

        Returns:
            str: The formatted SQL string for the update function and trigger.
        """

        prop_key_str = ""
        prop_val_str = ""
        if self.properties:
            prop_key_str = "SET " + ", ".join(
                f"v.{prop.accessor} = %s" for prop in self.properties
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
        Generates the SQL string for creating a delete function and trigger.

        This function constructs an SQL command that uses the `cypher` function to
        delete a relationship between two vertices in a graph database. The vertices
        and the relationship are specified by the attributes of the class instance.

        Returns:
            str: The formatted SQL string for deleting the specified relationship.
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
        Generates the SQL command to create a function and trigger for truncating
        relationships in a graph database.

        This method constructs a SQL string that uses the `cypher` function to
        match and delete a relationship between two vertices in a graph. The
        vertices and relationship are specified by the `start_vertex`,
        `end_vertex`, and `label` attributes of the class instance.

        Returns:
            str: The formatted SQL command string.
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
