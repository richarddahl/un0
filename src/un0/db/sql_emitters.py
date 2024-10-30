# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from abc import ABC, abstractmethod
from datetime import datetime, date, time
from decimal import Decimal
from typing import Type, ClassVar, Callable

from pydantic import BaseModel, ConfigDict, computed_field
from pydantic.dataclasses import dataclass
from dataclasses import field

from sqlalchemy import (
    Table,
    Column,
    Index,
    ForeignKey,
    text,
    CheckConstraint,
    UniqueConstraint,
)

from un0.utilities import convert_snake_to_capital_word
from un0.fltr.enums import (
    GraphType,
    EdgeDirection,
    Lookup,
    related_lookups,
    numeric_lookups,
    string_lookups,
)
from un0.config import settings
from un0.db.rls_policy_sql import (
    user_select_policy_sql,
    user_insert_policy_sql,
    user_update_policy_sql,
    user_delete_policy_sql,
    admin_select_policy_sql,
    admin_insert_policy_sql,
    admin_update_policy_sql,
    admin_delete_policy_sql,
    default_select_policy_sql,
    default_insert_policy_sql,
    default_update_policy_sql,
    default_delete_policy_sql,
)


@dataclass
class SQLEmitter(ABC):
    """
    SQLEmitter is an abstract base class that provides methods to generate SQL statements for database operations.

    Attributes:
        table_name (str): The name of the table.
        db_schema (str): The schema of the database.

    Methods:
        emit_sql() -> str:
            Abstract method that must be implemented by subclasses to emit SQL statements for database changes.

        create_sql_trigger(
            db_function: bool = True
            Generates a SQL trigger statement.

            Args:
                function_name (str): The name of the function to be triggered.
                timing (str, optional): The timing of the trigger (default is "BEFORE").
                operation (str, optional): The operation that activates the trigger (default is "UPDATE").
                for_each (str, optional): The level at which the trigger is executed (default is "ROW").
                db_function (bool, optional): Whether the function is a database-level function (default is True).

            Returns:
                str: The SQL trigger statement.

        create_sql_function(
            security_definer: str = ""
            Generates a SQL function statement and optionally a trigger statement.

            Args:
                function_name (str): The name of the function.
                function_string (str): The body of the function.
                db_function (bool, optional): Whether the function is a database-level function (default is True).
                return_type (str, optional): The return type of the function (default is "TRIGGER").
                volatile (str, optional): The volatility of the function (default is "VOLATILE").
                include_trigger (bool, optional): Whether to include a trigger statement (default is False).
                timing (str, optional): The timing of the trigger (default is "BEFORE").
                operation (str, optional): The operation that activates the trigger (default is "UPDATE").
                for_each (str, optional): The level at which the trigger is executed (default is "ROW").
                security_definer (str, optional): The security definer clause (default is "").

            Returns:
                str: The SQL function statement, and optionally the trigger statement.
    """

    table_name: str
    db_schema: str

    @abstractmethod
    def emit_sql(self) -> str:
        """
        Emits the SQL statements to make changes to the database.

        Returns:
            str: The SQL statements as a string.

        Raises:
            NotImplementedError: If the method is not implemented.
        """
        """Emits the SQL statements to makde changes for the database."""
        raise NotImplementedError

    def create_sql_trigger(
        self,
        function_name: str,
        timing: str = "BEFORE",
        operation: str = "UPDATE",
        for_each: str = "ROW",
        db_function: bool = True,
    ) -> str:
        """
        Generates a SQL statement to create or replace a trigger for a specified table.

        Args:
            function_name (str): The name of the function to be executed by the trigger.
            timing (str, optional): The timing of the trigger execution. Defaults to "BEFORE".
            operation (str, optional): The operation that activates the trigger. Defaults to "UPDATE".
            for_each (str, optional): Specifies whether the trigger is for each row or statement. Defaults to "ROW".
            db_function (bool, optional): Indicates whether the function is a database-level function or table-specific. Defaults to True.

        Returns:
            str: The SQL statement to create or replace the trigger.
        """
        # Used to differentiate between db and table-specific functions
        trigger_scope = (
            self.db_schema if db_function else f"{self.db_schema}.{self.table_name}"
        )
        return textwrap.dedent(
            f"CREATE OR REPLACE TRIGGER {self.table_name}_{function_name}_trigger\n"
            f"    {timing} {operation}\n"
            f"    ON {self.db_schema}.{self.table_name}\n"
            f"    FOR EACH {for_each}\n"
            f"    EXECUTE FUNCTION {trigger_scope}_{function_name}();\n"
        )

    def create_sql_function(
        self,
        function_name: str,
        function_string: str,
        db_function: bool = True,
        return_type: str = "TRIGGER",
        volatile: str = "VOLATILE",
        include_trigger: bool = False,
        timing: str = "BEFORE",
        operation: str = "UPDATE",
        for_each: str = "ROW",
        security_definer: str = "",
    ) -> str:
        """
        Creates a SQL function and optionally a trigger for a PostgreSQL database.

        Args:
            function_name (str): The name of the function to create.
            function_string (str): The body of the function.
            db_function (bool, optional): If True, the function is created as a database function.
                                          If False, it is created as a table-specific function.
                                          Defaults to True.
            return_type (str, optional): The return type of the function. Defaults to "TRIGGER".
            volatile (str, optional): The volatility of the function. Defaults to "VOLATILE".
            include_trigger (bool, optional): If True, a trigger is created for the function.
                                              Defaults to False.
            timing (str, optional): The timing of the trigger (e.g., "BEFORE", "AFTER").
                                    Defaults to "BEFORE".
            operation (str, optional): The operation that fires the trigger (e.g., "INSERT", "UPDATE").
                                       Defaults to "UPDATE".
            for_each (str, optional): Specifies whether the trigger fires for each row or statement.
                                      Defaults to "ROW".
            security_definer (str, optional): Specifies the security context in which the function is executed.
                                              Defaults to an empty string.

        Returns:
            str: The SQL statement to create the function and optionally the trigger.
        """
        full_function_name = (
            f"{self.db_schema}.{function_name}"
            if db_function
            else f"{self.db_schema}.{self.table_name}_{function_name}"
        )
        fnct_string = textwrap.dedent(
            f"CREATE OR REPLACE FUNCTION {full_function_name}()\n"
            f"RETURNS {return_type}\n"
            "LANGUAGE plpgsql\n"
            f"{volatile}\n"
            f"{security_definer}\n"
            "AS $BODY$\n"
            "BEGIN\n"
            f"  {function_string}\n"
            "END;\n"
            "$BODY$;\n"
        )
        if not include_trigger:
            return fnct_string
        trggr_string = self.create_sql_trigger(
            function_name,
            timing=timing,
            operation=operation,
            for_each=for_each,
            db_function=db_function,
        )
        return f"{textwrap.dedent(fnct_string)}\n{textwrap.dedent(trggr_string)}"


@dataclass
class BaseTableSQLEmitter(SQLEmitter):
    """
    BaseTableSQLEmitter is a subclass of SQLEmitter that provides methods to generate SQL statements
    for creating table type records and altering table ownership and privileges.

    Methods:
        emit_sql() -> str:
            Combines the SQL statements generated by `emit_create_table_type_record_sql` and
            `emit_alter_table_and_grant_privileges_sql` into a single string.

        emit_create_table_type_record_sql() -> str:
            Generates a SQL INSERT statement to add a new record to the `un0.tabletype` table with
            the schema and name provided by the instance's `db_schema` and `table_name` attributes.

        emit_alter_table_and_grant_privileges_sql() -> str:
            Generates a SQL command to change the owner of a table to the admin user and set
            privileges for reader and writer roles.
    """

    def emit_sql(self) -> str:
        """
        Generates and returns the SQL statements for creating a table type record
        and altering the table to grant privileges.

        Returns:
            str: The concatenated SQL statements for creating the table type record
                 and altering the table to grant privileges.
        """
        return (
            f"{self.emit_create_table_type_record_sql()}\n"
            f"{self.emit_alter_table_and_grant_privileges_sql()}\n"
        )

    def emit_create_table_type_record_sql(self) -> str:
        """
        Emits the SQL statement to insert a record into the `un0.tabletype` table.

        This method creates a SQL INSERT statement that adds a new record to the
        `un0.tabletype` table with the schema and name provided by the instance's
        `db_schema` and `table_name` attributes.

        Returns:
            str: A formatted SQL INSERT statement as a string.
        """
        return textwrap.dedent(
            f"""
            -- Create the tabletype record
            SET ROLE {settings.DB_NAME}_admin;
            INSERT INTO un0.tabletype (schema, name)
            VALUES ('{self.db_schema}', '{self.table_name}');
            """
        )

    def emit_alter_table_and_grant_privileges_sql(self) -> str:
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
            ALTER TABLE {self.db_schema}.{self.table_name} OWNER TO {settings.DB_NAME}_admin;
            GRANT SELECT ON {self.db_schema}.{self.table_name} TO
                {settings.DB_NAME}_reader,
                {settings.DB_NAME}_writer;
            GRANT INSERT, UPDATE, DELETE ON {self.db_schema}.{self.table_name} TO
                {settings.DB_NAME}_writer;
            """
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
                 `self.db_schema` and `self.table_name`.
        """
        return textwrap.dedent(
            f"""
            -- Enable auditing for the table
            SELECT audit.enable_tracking('{self.db_schema}.{self.table_name}'::regclass);
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
            The history table will be created in the 'audit' schema and will have the same
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

        The history table will be created in the 'audit' schema and will have the same structure
        as the original table, but without any data. Additionally, it will have an auto-incrementing
        primary key column and two indexes: one on the primary key and another on the combination
        of 'id' and 'modified_at' columns.

        Returns:
            str: A SQL statement to create the history table.
        """
        return textwrap.dedent(
            f"""
            SET ROLE {settings.DB_NAME}_admin;
            CREATE TABLE audit.{self.db_schema}_{self.table_name}
            AS (SELECT * FROM {self.db_schema}.{self.table_name})
            WITH NO DATA;

            ALTER TABLE audit.{self.db_schema}_{self.table_name}
            ADD COLUMN pk INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY;

            CREATE INDEX {self.db_schema}_{self.table_name}_pk_idx
            ON audit.{self.db_schema}_{self.table_name} (pk);

            CREATE INDEX {self.db_schema}_{self.table_name}_id_modified_at_idx
            ON audit.{self.db_schema}_{self.table_name} (id, modified_at);
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
        function_string = (
            f"SET ROLE {settings.DB_NAME}_admin;\n"
            f"INSERT INTO audit.{self.db_schema}_{self.table_name}"
            "SELECT *\n"
            f"FROM {self.db_schema}.{self.table_name}\n"
            "WHERE id = NEW.id;\n"
            "RETURN NEW;\n"
        )
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
class TrashSQLEmitter(SQLEmitter):
    def emit_sql(self) -> str:
        """
        Generates a SQL trigger creation statement for validating deletions.

        This method creates a SQL trigger named `validate_delete_trigger` that is
        executed before a delete operation on the specified table. The trigger
        calls the `un0.validate_delete()` function to perform validation.

        Returns:
            str: A SQL statement for creating the `validate_delete_trigger`.
        """
        return self.create_sql_trigger("validate_delete", operation="DELETE")


@dataclass
class CreatedModifiedSQLEmitter(SQLEmitter):
    def emit_sql(self) -> str:
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
        return self.create_sql_trigger(
            "set_owner_and_modified", operation="INSERT OR UPDATE"
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


@dataclass
class RLSSQLEmitter(SQLEmitter):
    insert_policy: Callable | str
    select_policy: Callable | str
    delete_policy: Callable | str
    update_policy: Callable | str
    force_rls: bool = True

    def emit_sql(self) -> str:
        """
        Generates and returns the SQL statements for enabling RLS, forcing RLS,
        and applying select, insert, update, and delete policies.

        Returns:
            str: A string containing the concatenated SQL statements, separated by newlines.
        """
        sql = [
            self.emit_enable_rls_sql(),
            self.emit_force_rls_sql() if self.force_rls else "",
            self.select_policy(self.db_schema, self.table_name)
            if callable(self.select_policy)
            else self.select_policy,
            self.insert_policy(self.db_schema, self.table_name)
            if callable(self.insert_policy)
            else self.insert_policy,
            self.update_policy(self.db_schema, self.table_name)
            if callable(self.update_policy)
            else self.update_policy,
            self.delete_policy(self.db_schema, self.table_name)
            if callable(self.delete_policy)
            else self.delete_policy,
        ]
        return "\n".join(sql)

    def emit_enable_rls_sql(self) -> str:
        """
        Emits the SQL statements to enable Row Level Security (RLS)
        on the table.

        Returns:
            str: A string containing the SQL statements to enable RLS for the table.
        """
        return textwrap.dedent(
            f"""
            -- Enable RLS for the table {self.db_schema}.{self.table_name}
            SET ROLE {settings.DB_NAME}_admin;
            ALTER TABLE {self.db_schema}.{self.table_name} ENABLE ROW LEVEL SECURITY;
            """
        )

    def emit_force_rls_sql(self) -> str:
        """
        Emits the SQL statements to force Row Level Security (RLS)
        on the table for table owners and db superusers.

        Returns:
            str: A string containing the SQL statements to force RLS for the table.
        """
        return textwrap.dedent(
            f"""
            -- FORCE RLS for the table {self.db_schema}.{self.table_name}
            SET ROLE {settings.DB_NAME}_admin;
            ALTER TABLE {self.db_schema}.{self.table_name} FORCE ROW LEVEL SECURITY;
            """
        )


@dataclass
class UserRLSSQLEmitter(RLSSQLEmitter):
    select_policy: Callable = user_select_policy_sql
    insert_policy: Callable = user_insert_policy_sql
    update_policy: Callable = user_update_policy_sql
    delete_policy: Callable = user_delete_policy_sql


@dataclass
class DefaultRLSSQLEmitter(RLSSQLEmitter):
    select_policy: Callable = default_select_policy_sql
    insert_policy: Callable = default_insert_policy_sql
    update_policy: Callable = default_update_policy_sql
    delete_policy: Callable = default_delete_policy_sql


@dataclass
class AdminRLSSQLEmitter(RLSSQLEmitter):
    select_policy: Callable = admin_select_policy_sql
    insert_policy: Callable = admin_insert_policy_sql
    update_policy: Callable = admin_update_policy_sql
    delete_policy: Callable = admin_delete_policy_sql


class GraphSQLEmitter(SQLEmitter):
    """ """

    # vertex: VertexSqlEmitter <- computed_field
    # edges: list[EdgeSqlEmitter] <- computed_field
    # properties: list[PropertySqlEmitter] <- computed_field

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
        Generates a list of EdgeSqlEmitter objects representing the edges in the database schema.

        This method iterates over the foreign keys of the table and their corresponding columns to create
        EdgeSqlEmitter instances. Each EdgeSqlEmitter represents a relationship between two vertices (start and end)
        in the schema.

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
    PropertySqlEmitter is a subclass of TableManager that represents the schema for a property in a database table.
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


class VertexSqlEmitter(SQLEmitter):
    """
    VertexSqlEmitter is a subclass of TableManager that represents the schema for a vertex in a graph database.
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


class EdgeSqlEmitter(SQLEmitter):
    """
    EdgeSqlEmitter is a class that represents the schema for an edge in a graph database. It extends the TableManager class and includes additional attributes and methods specific to edges.
    Attributes:
        table (Table): The table associated with the edge.
        to_column (Column): The column representing the edge.
        start_vertex (VertexSqlEmitter): The schema of the start vertex.
        end_vertex (VertexSqlEmitter): The schema of the end vertex.
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
