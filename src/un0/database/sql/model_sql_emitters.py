# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from datetime import datetime, date, time
from decimal import Decimal

from pydantic import ConfigDict, computed_field
from pydantic.dataclasses import dataclass

from sqlalchemy import (
    Table,
    Column,
)

from un0.utilities import convert_snake_to_capital_word
from un0.filters.enums import (
    GraphType,
    EdgeDirection,
    Lookup,
    related_lookups,
    numeric_lookups,
    string_lookups,
)
from un0.database.sql.sql_emitter import SQLEmitter
from un0.config import settings


@dataclass
class BaseTableSQLEmitter(SQLEmitter):
    def emit_sql(self) -> str:
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
            SET ROLE {settings.DB_NAME}_admin;
            ALTER TABLE {self.schema_name}.{self.table_name} OWNER TO {settings.DB_NAME}_admin;
            GRANT SELECT ON {self.schema_name}.{self.table_name} TO
                {settings.DB_NAME}_reader,
                {settings.DB_NAME}_writer;
            GRANT INSERT, UPDATE, DELETE ON {self.schema_name}.{self.table_name} TO
                {settings.DB_NAME}_writer;
            """
        )


@dataclass
class RelatedObjectSQLEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        return f"{self.emit_create_table_type_record_sql()}\n{self.emit_create_related_object_sql()}"

    def emit_create_table_type_record_sql(self) -> str:
        """
        Emits the SQL statement to insert a record into the `un0.table_type` table.

        This method creates a SQL INSERT statement that adds a new record to the
        `un0.table_type` table with the schema_name and name provided by the instance's
        `schema_name` and `table_name` attributes.

        Returns:
            str: A formatted SQL INSERT statement as a string.
        """
        return textwrap.dedent(
            f"""
            -- Create the table_type record
            SET ROLE {settings.DB_NAME}_admin;
            INSERT INTO un0.table_type (db_schema, name)
            VALUES ('{self.schema_name}', '{self.table_name}')
            ON CONFLICT DO NOTHING;

            -- Change the table default for id
            ALTER TABLE {self.schema_name}.{self.table_name}
            ALTER COLUMN id SET DEFAULT un0.generate_ulid();
            """
        )

    def emit_create_related_object_sql(self) -> str:
        function_string = """
            DECLARE
                rel_obj_id VARCHAR(26);
                table_type_id INT;
            BEGIN
                /*
                Function used to insert a record into the related_object table, when a record is inserted
                into a table that has a PK that is a FK to the related_object table.
                */
                SELECT id
                    FROM un0.table_type
                    WHERE db_schema = TG_TABLE_SCHEMA AND name = TG_TABLE_NAME
                    INTO table_type_id;

                INSERT INTO un0.related_object (id, table_type_id)
                VALUES (NEW.id, table_type_id)
                ON CONFLICT DO NOTHING;
                RETURN NEW;
            END;
            """

        return self.create_sql_function(
            "insert_related_object",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=True,
        )


@dataclass
class DefaultAuditSQLEmitter(SQLEmitter):
    """
    A class that generates SQL statements to enable auditing for a specified table.

    Methods
    -------
    emit_sql() -> str
        Generates and returns the SQL statement to enable auditing for the table.
    """

    def emit_sql(self) -> str:
        """
        Generates and returns a SQL string to enable auditing for a specific table.

        Returns:
            str: A SQL string that enables auditing for the table specified by
                 `self.schema_name` and `self.table_name`.
        """
        return textwrap.dedent(
            f"""
            -- Enable auditing for the table
            SELECT audit.enable_tracking('{self.schema_name}.{self.table_name}'::regclass);
            """
        )


@dataclass
class HistoryAuditSQLEmitter(SQLEmitter):
    """
    HistoryAuditSQLEmitter is a specialized SQLEmitter that generates SQL statements for creating
    a history table, along with the associated function and trigger for auditing purposes.

    Methods:
        emit_sql() -> str:

        emit_create_history_table_sql() -> str:
            The history table will be created in the 'audit' schema_name and will have the same
            structure as the original table, but without any data. Additionally, it will
            have an auto-incrementing primary key column and two indexes: one on the primary
            key and another on the combination of 'id' and 'modified_at' columns.

        emit_create_history_function_and_trigger_sql() -> str:
            Generates the SQL statement for creating a function and trigger to insert
            records into the history table whenever an insert or update operation occurs
            on the original table.
    """

    def emit_sql(self) -> str:
        """
        Generates and returns the SQL statements for creating a history table and
        the associated function and trigger.

        Returns:
            str: A string containing the SQL statements.
        """
        return textwrap.dedent(
            f"{self.emit_create_history_table_sql()}\n{self.emit_create_history_function_and_trigger_sql()}"
        )

    def emit_create_history_table_sql(self) -> str:
        """
        Creates a SQL statement to generate a history table for auditing purposes.

        The history table will be created in the 'audit' schema_name and will have the same structure
        as the original table, but without any data. Additionally, it will have an auto-incrementing
        primary key column and two indexes: one on the primary key and another on the combination
        of 'id' and 'modified_at' columns.

        Returns:
            str: A SQL statement to create the history table.
        """
        return textwrap.dedent(
            f"""
            SET ROLE {settings.DB_NAME}_admin;
            CREATE TABLE audit.{self.schema_name}_{self.table_name}
            AS (SELECT * FROM {self.schema_name}.{self.table_name})
            WITH NO DATA;

            ALTER TABLE audit.{self.schema_name}_{self.table_name}
            ADD COLUMN pk INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;

            CREATE INDEX {self.schema_name}_{self.table_name}_pk_idx
            ON audit.{self.schema_name}_{self.table_name} (pk);

            CREATE INDEX {self.schema_name}_{self.table_name}_id_modified_at_idx
            ON audit.{self.schema_name}_{self.table_name} (id, modified_at);
            """
        )

    def emit_create_history_function_and_trigger_sql(self) -> str:
        """
        Generates SQL code to create a history function and trigger for a specified table.

        The function and trigger are designed to insert a record into an audit table
        whenever a new record is inserted or an existing record is updated in the target table.
        The function is created with SECURITY DEFINER to ensure it runs with the necessary permissions.

        Returns:
            str: The SQL code to create the history function and trigger.
        """
        function_string = f"""
            INSERT INTO audit.{self.schema_name}_{self.table_name}
            SELECT *
            FROM {self.schema_name}.{self.table_name}
            WHERE id = NEW.id;
            RETURN NEW;
            """

        return self.create_sql_function(
            "history",
            function_string,
            timing="AFTER",
            operation="INSERT OR UPDATE",
            include_trigger=True,
            db_function=False,
            security_definer="SECURITY DEFINER",
        )


@dataclass
class CreatedModifiedSQLEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = """
            DECLARE
                user_id VARCHAR(26) := current_setting('rls_var.id', true);
                estimate INT;
            BEGIN
                /* 
                Function used to set the owner_id and modified_by_id fields
                of a table to the user_id of the user making the change. 
                */

                SELECT current_setting('rls_var.id', true) INTO user_id;

                IF user_id IS NULL THEN
                    /*
                    This should only happen when the very first user is created
                    and therefore a user_id cannot be set in the session variables
                    */
                    SELECT reltuples AS estimate FROM PG_CLASS WHERE relname = TG_TABLE_NAME INTO estimate;
                    IF TG_TABLE_NAME = 'user' AND estimate < 1 THEN
                        RETURN NEW;
                    ELSE
                        RAISE EXCEPTION 'user_id is NULL';
                    END IF;
                END IF;

                IF user_id = '' THEN
                    RAISE EXCEPTION 'user_id is an empty string';
                END IF;

                IF TG_OP = 'INSERT' THEN
                    NEW.owner_id = user_id;
                    NEW.modified_by_id = user_id;
                    NEW.created_at := TIMESTAMPZ();
                END IF;

                IF TG_OP = 'UPDATE' THEN
                    NEW.modified_by_id = user_id;
                END IF;

                NEW.modified_at := NOW();
                RETURN NEW;
            END;
            """

        return self.create_sql_function(
            "set_owner_and_modified",
            function_string,
            timing="BEFORE",
            operation="INSERT OR UPDATE",
            include_trigger=True,
            db_function=True,
        )


@dataclass
class SoftDeleteSQLEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = """
            DECLARE
                user_id VARCHAR(26);
            BEGIN
                /* 
                Function used to validate that a record can be deleted.
                IF the record previously had is_deleted set to false the function
                returns the record, allowing the delete to proceed.
                otherwise Sets the is_deleted field to true and the deleted_by_id field to the user_id
                */

                SELECT current_setting('rls_var.id', true) into user_id;

                IF user_id IS NULL THEN
                    RAISE EXCEPTION 'user_id is NULL';
                END IF;

                IF OLD.is_deleted IS TRUE THEN
                    OLD.deleted_by_id = user_id;
                    OLD.deleted_at = NOW();
                    RETURN OLD;
                ELSE
                    EXECUTE format('
                        UPDATE %I 
                        SET is_deleted = true, deleted_by_id = %L , deleted_at = NOW()
                        WHERE id = %L', TG_TABLE_NAME, user_id, OLD.id
                    );
                    RETURN NULL;
                END IF;
            END;
            """

        return self.create_sql_function(
            "validate_delete",
            function_string,
            timing="BEFORE",
            operation="DELETE",
            include_trigger=True,
            db_function=True,
        )


@dataclass
class TablePermissionSQLEmitter(SQLEmitter):
    def emit_create_table_record_sql(self) -> str:
        function_string = """
            BEGIN
                /*
                Function to create a new TablePermission record when a new TableType is inserted.
                Records are created for each table_type with the following combinations of permissions:
                    [SELECT]
                    [SELECT, INSERT]
                    [SELECT, UPDATE]
                    [SELECT, INSERT, UPDATE]
                    [SELECT, INSERT, UPDATE, DELETE]
                Deleted automatically by the DB via the FK Constraints ondelete when a table_type is deleted.
                */
                INSERT INTO un0.tablepermission(table_type_id, actions)
                    VALUES (NEW.id, ARRAY['SELECT']::un0.permission_name[]);
                INSERT INTO un0.tablepermission(table_type_id, actions)
                    VALUES (NEW.id, ARRAY['SELECT', 'INSERT']::un0.permission_name[]);
                INSERT INTO un0.tablepermission(table_type_id, actions)
                    VALUES (NEW.id, ARRAY['SELECT', 'UPDATE']::un0.permission_name[]);
                INSERT INTO un0.tablepermission(table_type_id, actions)
                    VALUES (NEW.id, ARRAY['SELECT', 'INSERT', 'UPDATE']::un0.permission_name[]);
                INSERT INTO un0.tablepermission(table_type_id, actions)
                    VALUES (NEW.id, ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']::un0.permission_name[]);
                RETURN NEW;
            END;
            """

        return self.create_sql_function(
            "create_tablepermissions_trigger",
            function_string,
            timing="AFTER",
            operation="INSERT",
            include_trigger=True,
            db_function=True,
        )

    def emit_get_permissions_function_sql(self) -> str:
        function_string = f"""
            SET ROLE {settings.DB_NAME}_admin;
            DECLARE
                session_user_id := current_setting('session_user_id', true);
            BEGIN
                SELECT g.*
                from group g
                JOIN un0.user_group_role ugr ON ugr.group_id = g.id
                JOIN un0.user u ON u.id = ugr.user_email
                JOIN un0.tablepermission tp ON ugr.role_id = tp.id
                WHERE u.id = session_user_id AND tp.is_active = TRUE
                AND tp.table_name = query_table_name;
            END;
            """

        return self.create_sql_function("get_permissible_groups", function_string)


class ValidateGroupInsertSQLEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                group_count INT4;
                tenanttype un0.tenanttype;
            BEGIN
                SELECT tenant_type INTO tenanttype
                FROM un0.tenant
                WHERE id = NEW.tenant_id;

                SELECT COUNT(*) INTO group_count
                FROM un0.group
                WHERE tenant_id = NEW.tenant_id;

                IF NOT {settings.ENFORCE_MAX_GROUPS} THEN
                    RETURN NEW;
                END IF;

                IF tenanttype = 'INDIVIDUAL' AND
                    {settings.MAX_INDIVIDUAL_GROUPS} > 0 AND
                    group_count >= {settings.MAX_INDIVIDUAL_GROUPS} THEN
                        RAISE EXCEPTION 'Group Count Exceeded';
                END IF;
                IF
                    tenanttype = 'BUSINESS' AND
                    {settings.MAX_BUSINESS_GROUPS} > 0 AND
                    group_count >= {settings.MAX_BUSINESS_GROUPS} THEN
                        RAISE EXCEPTION 'Group Count Exceeded';
                END IF;
                IF
                    tenanttype = 'CORPORATE' AND
                    {settings.MAX_CORPORATE_GROUPS} > 0 AND
                    group_count >= {settings.MAX_CORPORATE_GROUPS} THEN
                        RAISE EXCEPTION 'Group Count Exceeded';
                END IF;
                IF
                    tenanttype = 'ENTERPRISE' AND
                    {settings.MAX_ENTERPRISE_GROUPS} > 0 AND
                    group_count >= {settings.MAX_ENTERPRISE_GROUPS} THEN
                        RAISE EXCEPTION 'Group Count Exceeded';
                END IF;
                RETURN NEW;
            END;
            """

        return self.create_sql_function(
            "validate_group_insert",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=False,
        )


'''
@dataclass
class PrivateFieldSQLEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        """
        """
        return self.create_sql_trigger(
            "set_owner_and_modified", operation="INSERT OR UPDATE"
        )
'''


class GraphSQLEmitter(SQLEmitter):
    """ """

    # vertex: VertexSqlEmitter <- computed_field
    # edges: list[EdgeSqlEmitter] <- computed_field
    # properties: list[PropertySqlEmitter] <- computed_field
    create_vertex: bool = True

    @computed_field
    def vertex(self) -> bool:
        """
        Determines if the table is a vertex and returns a VertexSqlEmitter instance if true.

        Returns:
            VertexSqlEmitter: An instance of VertexSqlEmitter if the table is a vertex.
            bool: False if the table is not a vertex.
        """
        if self.table.info.get("vertex", True) is not False:
            return VertexSqlEmitter(
                table=self.table, column=self.table.primary_key.columns[0]
            )

    @computed_field
    def edges(self) -> list["EdgeSqlEmitter"] | None:
        """
        Generates a list of EdgeSqlEmitter objects representing the edges in the database schema_name.

        This method iterates over the foreign keys of the table and their corresponding columns to create
        EdgeSqlEmitter instances. Each EdgeSqlEmitter represents a relationship between two vertices (start and end)
        in the schema_name.

        Returns:
            list[EdgeSqlEmitter] | None: A list of EdgeSqlEmitter objects if any edges are found, otherwise None.
        """
        edges = []
        for fk in self.table.foreign_keys:
            for column in self.table.columns:
                if fk.parent.name == column.name:
                    continue
                for _fk in column.foreign_keys:
                    edges.append(
                        EdgeSqlEmitter(
                            table=self.table,
                            to_column=column,
                            start_vertex=VertexSqlEmitter(
                                table=self.table,
                                column=fk.parent,
                            ),
                            end_vertex=VertexSqlEmitter(
                                table=fk.column.table,
                                column=fk.column,
                            ),
                        )
                    )
        return edges

    @computed_field
    def properties(self) -> list["PropertySqlEmitter"] | None:
        """
        Retrieves a list of PropertySqlEmitter objects for each column in the table.

        Returns:
            list[PropertySqlEmitter] | None: A list of PropertySqlEmitter objects representing
            the properties of each column in the table, or None if there are no columns.
        """
        props = []
        for column in self.table.columns:
            props.append(PropertySqlEmitter(table=self.table, column=column))
        return props


class PropertySqlEmitter(SQLEmitter):
    """
    PropertySqlEmitter is a subclass of TableManager that represents the schema_name for a property in a database table.
    It includes computed fields and methods to generate SQL statements for creating filter fields and their
    associated table types.

    Attributes:
        column (Column): The column associated with the property schema_name.
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
           - The relationship is defined by the `filterfield_id`, `table_type_id`, and `direction`.
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
                table_type_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.FROM.name}'
            FROM un0.filterfield f
            JOIN un0.table_type t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.PROPERTY.name}'
            AND t.name = '{self.table_name}'
            AND t.schema_name = '{self.schema_name}'
            ON CONFLICT DO NOTHING;
            """
        )


class VertexSqlEmitter(SQLEmitter):
    """
    VertexSqlEmitter is a subclass of TableManager that represents the schema_name for a vertex in a graph database.
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
        properties (list[PropertySqlEmitter] | None): A list of PropertySqlEmitter instances for each column in the table.
        edges (list[EdgeSqlEmitter] | None): A list of EdgeSqlEmitter objects representing the foreign key relationships of the table.

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
    # properties: list[PropertySqlEmitter] | None <- computed_field
    # edges: list[EdgeSqlEmitter] | None <- computed_field

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
    def properties(self) -> list["PropertySqlEmitter"] | None:
        """
        Generates a list of PropertySqlEmitter instances for each column in the table.

        Returns:
            list[PropertySqlEmitter] | None: A list of PropertySqlEmitter instances or None if no columns are present.
        """
        props = []
        for column in self.table.columns:
            props.append(PropertySqlEmitter(table=self.table, column=column))
        return props

    @computed_field
    def edges(self) -> list["EdgeSqlEmitter"] | None:
        """
        Generates a list of EdgeSqlEmitter objects representing the foreign key relationships
        of the table associated with this instance.

        Returns:
            list[EdgeSqlEmitter] | None: A list of EdgeSqlEmitter objects if foreign keys are present,
            otherwise None.
        """
        edges = []
        for fk in self.table.foreign_keys:
            edges.append(
                EdgeSqlEmitter(
                    table=self.table,
                    to_column=fk.parent,
                    start_vertex=self,
                    end_vertex=VertexSqlEmitter(
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
                table_type_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.FROM.name}'
            FROM un0.filterfield f
            JOIN un0.table_type t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.VERTEX.name}'
            AND t.name = '{self.table_name}'
            AND t.schema_name = '{self.schema_name}'
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
            f"-- Create the vertex label and index\n"
            f"DO $$ \n"
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


class EdgeSqlEmitter(SQLEmitter):
    """
    EdgeSqlEmitter is a class that represents the schema_name for an edge in a graph database. It extends the TableManager class and includes additional attributes and methods specific to edges.
    Attributes:
        table (Table): The table associated with the edge.
        to_column (Column): The column representing the edge.
        start_vertex (VertexSqlEmitter): The schema_name of the start vertex.
        end_vertex (VertexSqlEmitter): The schema_name of the end vertex.
        lookups (list[Lookup]): A list of related lookups.
        in_vertex (bool): A flag indicating if the edge is in a vertex. Defaults to True.
        model_config (dict): Configuration for the model, allowing arbitrary types.
    Methods:
        label() -> str:
            Computes and returns the label for the edge.
        accessor() -> str:
            Computes and returns the accessor for the edge.
        properties() -> list["PropertySqlEmitter"]:
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
    # properties: list[PropertySqlEmitter] <- computed_field

    table: Table
    to_column: Column
    start_vertex: VertexSqlEmitter
    end_vertex: VertexSqlEmitter
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
    def properties(self) -> list["PropertySqlEmitter"]:
        """
        Retrieves a list of PropertySqlEmitter objects for the current table.

        Returns:
            list[PropertySqlEmitter]: A list of PropertySqlEmitter objects representing
            the properties of the table's columns that are not foreign keys.
        """
        props = []
        if not self.in_vertex:
            for column in self.table.columns:
                if not column.foreign_keys:
                    props.append(PropertySqlEmitter(table=self.table, column=column))
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
                table_type_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.FROM.name}'
            FROM un0.filterfield f
            JOIN un0.table_type t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.EDGE.name}'
            AND t.name = '{self.table_name}'
            AND t.schema_name = '{self.schema_name}'
            ON CONFLICT DO NOTHING;
    
            INSERT INTO un0.filterfield_tabletype (
                filterfield_id,
                table_type_id,
                direction
            )
            SELECT f.id, t.id, '{EdgeDirection.TO.name}'
            FROM un0.filterfield f
            JOIN un0.table_type t
            ON f.label = '{self.label}'
            AND f.graph_type = '{GraphType.EDGE.name}'
            AND t.name = '{self.end_vertex.table.name}'
            AND t.schema_name = '{self.end_vertex.table.schema_name}'
            ON CONFLICT DO NOTHING;
            """
        )

    def create_label_sql(self) -> str:
        """
        Generates a SQL statement to create a label in the AgensGraph database if it does not already exist.

        Returns:
            str: A SQL statement that checks for the existence of a label in the ag_catalog.ag_label table.
                 If the label does not exist, it creates the label and an index on the 'graph' schema_name.
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
