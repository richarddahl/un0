# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from typing import Optional
from abc import ABC, abstractmethod
from pydantic.dataclasses import dataclass

from un0.config import settings


@dataclass
class SQLEmitter(ABC):
    """
    A base class for SQL query emission in PostgreSQL databases.

    This abstract class provides functionality for creating SQL functions and triggers,
    with methods to generate SQL statements for database operations.

    Attributes:
        table_name (Optional[str]): The name of the table this emitter operates on.
        schema_name (Optional[str]): The database schema name.
        field_name (Optional[str]): The name of the field, if applicable.

    Methods:
        emit_sql(): Abstract method that must be implemented by subclasses to generate SQL.
        create_sql_trigger(): Creates a SQL trigger statement.
        create_sql_function(): Creates a SQL function statement, optionally with a trigger.

    Example:
        ```python
        class MyEmitter(SQLEmitter):
            table_name = "my_table"
            schema_name = "public"

            def emit_sql(self):
                return "SELECT * FROM public.my_table;"
        ```

    Note:
        This class is designed to be subclassed, not used directly.
        The emit_sql() method must be implemented by all concrete subclasses.
    """

    table_name: Optional[str] = None
    schema_name: Optional[str] = None
    field_name: Optional[str] = None

    @abstractmethod
    def emit_sql(self) -> str:
        """
        Emits SQL statement based on the specific implementation.

        This method should be overridden by subclasses to generate appropriate SQL
        statements according to their specific requirements.

        Returns:
            str: A valid SQL statement string.

        Raises:
            NotImplementedError: When called directly on base class without implementation.
        """
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
        Creates a SQL trigger statement for a given table and function.

        This method generates a SQL statement that creates or replaces a trigger which executes
        a specified function based on database events.

        Parameters:
            function_name (str): Name of the function to be executed by the trigger
            timing (str, optional): When the trigger should fire ('BEFORE', 'AFTER', etc.). Defaults to 'BEFORE'
            operation (str, optional): Database operation that activates the trigger ('INSERT', 'UPDATE', 'DELETE'). Defaults to 'UPDATE'
            for_each (str, optional): Whether to fire for each row or statement ('ROW', 'STATEMENT'). Defaults to 'ROW'
            db_function (bool, optional): If True, function is at schema level. If False, function is table-specific. Defaults to True

        Returns:
            str: SQL statement that creates the trigger

        Example:
            >>> obj.create_sql_trigger('validate_data', 'BEFORE', 'INSERT')
            'CREATE OR REPLACE TRIGGER table_validate_data_trigger
             BEFORE INSERT ON schema.table
             FOR EACH ROW
             EXECUTE FUNCTION schema.validate_data();'
        """
        trigger_scope = (
            f"{self.schema_name}."
            if db_function
            else f"{self.schema_name}.{self.table_name}_"
        )
        return textwrap.dedent(
            f"""
            CREATE OR REPLACE TRIGGER {self.table_name}_{function_name}_trigger
                {timing} {operation}
                ON {self.schema_name}.{self.table_name}
                FOR EACH {for_each}
                EXECUTE FUNCTION {trigger_scope}{function_name}();
            """
        )

    def create_sql_function(
        self,
        function_name: str,
        function_string: str,
        function_args: str = "",
        db_function: bool = True,
        return_type: str = "TRIGGER",
        volatile: str = "VOLATILE",
        include_trigger: bool = False,
        timing: str = "BEFORE",
        operation: str = "UPDATE",
        for_each: str = "ROW",
        security_definer: str = "",
    ) -> str:
        """Creates a SQL function definition, optionally with an associated trigger.

        This method generates SQL for creating or replacing a PL/pgSQL function, with optional trigger creation.

        Args:
            function_name (str): Name of the function to create
            function_string (str): The PL/pgSQL function body
            function_args (str, optional): Function arguments declaration. Defaults to "".
            db_function (bool, optional): If True, uses schema name only. If False, prepends table name. Defaults to True.
            return_type (str, optional): SQL function return type. Defaults to "TRIGGER".
            volatile (str, optional): Function volatility setting. Defaults to "VOLATILE".
            include_trigger (bool, optional): Whether to create an associated trigger. Defaults to False.
            timing (str, optional): Trigger timing (BEFORE/AFTER/INSTEAD OF). Defaults to "BEFORE".
            operation (str, optional): Trigger operation (INSERT/UPDATE/DELETE). Defaults to "UPDATE".
            for_each (str, optional): Trigger granularity (ROW/STATEMENT). Defaults to "ROW".
            security_definer (str, optional): SECURITY DEFINER clause if needed. Defaults to "".

        Returns:
            str: SQL string for creating the function and optionally its trigger

        Raises:
            ValueError: If both function_args and include_trigger are specified
        """
        if function_args and include_trigger:
            raise ValueError(
                "Function arguments cannot be used when creating a trigger function."
            )
        full_function_name = (
            f"{self.schema_name}.{function_name}"
            if db_function
            else f"{self.schema_name}.{self.table_name}_{function_name}"
        )
        fnct_string = textwrap.dedent(
            f"""
            SET ROLE {settings.DB_NAME}_admin;
            CREATE OR REPLACE FUNCTION {full_function_name}({function_args})
            RETURNS {return_type}
            LANGUAGE plpgsql
            {volatile}
            {security_definer}
            AS $$
            {function_string}
            $$;
            """
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
class AlterGrantSQL(SQLEmitter):
    """
    A class used to generate SQL statements for altering table ownership and granting privileges.

    Methods
    -------
    emit_sql() -> str
        Generates and returns the SQL statement as a string.
    """

    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""
            SET ROLE {settings.DB_NAME}_admin;
            -- Congigure table ownership and privileges
            ALTER TABLE {self.schema_name}.{self.table_name} OWNER TO {settings.DB_NAME}_admin;
            GRANT SELECT ON {self.schema_name}.{self.table_name} TO
                {settings.DB_NAME}_reader,
                {settings.DB_NAME}_writer;
            GRANT INSERT, UPDATE, DELETE ON {self.schema_name}.{self.table_name} TO
                {settings.DB_NAME}_writer;
            """
        )


@dataclass
class InsertTableTypeSQL(SQLEmitter):
    """
    A class used to generate SQL for inserting a record into the table_type table.

    Methods
    -------
    emit_sql() -> str
        Generates and returns the SQL string for inserting a record into the table_type table.
    """

    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Create the table_type record
            INSERT INTO un0.table_type (db_schema, name)
            VALUES ('{self.schema_name}', '{self.table_name}');
            """
        )


@dataclass
class EnableDefaultAuditSQL(SQLEmitter):
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
class CreateHistoryTableSQL(SQLEmitter):
    """Creates an audit history table for a given schema and table.

    The history table is created in the audit schema with the same structure as the source table,
    plus an additional auto-incrementing primary key column. The history table is initially empty.

    The emitted SQL:
    1. Sets role to database admin
    2. Creates audit history table copying structure from source table
    3. Adds auto-incrementing primary key column
    4. Creates index on primary key
    5. Creates composite index on id and modified_at columns

    Parameters are passed through parent SQLEmitter class:
        schema_name (str): Schema of the source table
        table_name (str): Name of the source table

    Returns:
        str: SQL statement to create audit history table and indexes
    """

    def emit_sql(self) -> str:
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


class HistoryAuditFnctTrggrSQL(SQLEmitter):
    """
    Generates SQL for creating history function and trigger for audit tables.

    This class is responsible for creating SQL statements that set up history tracking
    functionality through functions and triggers. It inserts records into an audit table
    whenever INSERT or UPDATE operations occur on the tracked table.

    Inherits from SQLEmitter base class.

    Methods:
        emit_create_history_function_and_trigger_sql() -> str:
            Creates SQL statements for history tracking function and trigger.
            Returns formatted SQL string that:
            - Creates a function to copy records to the audit table
            - Creates an AFTER trigger that fires on INSERT or UPDATE
            - Uses SECURITY DEFINER for elevated permissions

    Example:
        emitter = HistoryAuditFnctTrggrSQL(schema='public', table='users')
        sql = emitter.emit_create_history_function_and_trigger_sql()
    """

    def emit_create_history_function_and_trigger_sql(self) -> str:
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
class SetDefaultActiveSQL(SQLEmitter):
    """Sets the default value of the 'active' column to TRUE for a specified table.

    This SQL emitter generates an ALTER TABLE statement to modify the default value
    of the 'active' column to TRUE in the specified schema and table.

    Inherits:
        SQLEmitter: Base class for SQL statement generation

    Returns:
        str: SQL statement that sets default value of 'active' column to TRUE
    """

    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Add the table default for active
            ALTER TABLE {self.schema_name}.{self.table_name}
                ALTER COLUMN is_active SET DEFAULT TRUE;
            """
        )


@dataclass
class SuperUserInsertSQL(SQLEmitter):
    """A SQL emitter that creates a trigger function to handle superuser-specific field insertions.

    This class generates SQL code for a trigger function that allows only superusers to insert
    values into specific fields. For non-superusers, the field value is set to NULL.

    The generated SQL includes:
    - A trigger function that checks if the current user is a superuser
    - Sets the field value to NULL for non-superusers
    - Preserves the original value for superusers
    - Creates both the function and associated trigger

    Attributes:
        field_name (str): The name of the database field to be protected by the trigger

    Returns:
        str: Complete SQL code for creating the trigger function and associated trigger

    """

    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
            BEGIN
                IF superuser THEN
                    NEW.{self.field_name} = NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} = NULL;
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_superuser_insert",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=False,
        )


@dataclass
class SuperUserUpdateSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
            BEGIN
                IF superuser THEN
                    NEW.{self.field_name} := NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} := OLD.{self.field_name};
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_superuser_update",
            function_string,
            timing="BEFORE",
            operation="UPDATE",
            include_trigger=True,
            db_function=False,
        )


@dataclass
class AdminInsertSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
                is_tenant_admin BOOLEAN := current_setting('rls_var.is_tenant_admin', true)::BOOLEAN;
            BEGIN
                IF is_superuser OR is_tenant_admin THEN
                    NEW.{self.field_name} = NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} = NULL;
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_admin_insert",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=False,
        )


@dataclass
class AdminUpdateSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
                is_tenant_admin BOOLEAN := current_setting('rls_var.is_tenant_admin', true)::BOOLEAN;
            BEGIN
                IF is_superuser OR is_tenant_admin THEN
                    NEW.{self.field_name} := NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} := OLD.{self.field_name};
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_admin_update",
            function_string,
            timing="BEFORE",
            operation="UPDATE",
            include_trigger=True,
            db_function=False,
        )


@dataclass
class OwnerInsertSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
                is_tenant_admin BOOLEAN := current_setting('rls_var.is_tenant_admin', true)::BOOLEAN;
                user_id TEXT := current_setting('rls_var.user_id', true)::TEXT;
            BEGIN
                IF is_superuser OR is_tenant_admin OR NEW.owned_by_id = user_id THEN
                    NEW.{self.field_name} = NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} = NULL;
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_owner_insert",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=False,
        )


@dataclass
class OwnerUpdateSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
                is_tenant_admin BOOLEAN := current_setting('rls_var.is_tenant_admin', true)::BOOLEAN;
                user_id TEXT := current_setting('rls_var.user_id', true)::TEXT;
            BEGIN
                IF is_superuser OR is_tenant_admin OR NEW.owned_by_id = user_id THEN
                    NEW.{self.field_name} := NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} := OLD.{self.field_name};
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_owner_update",
            function_string,
            timing="BEFORE",
            operation="UPDATE",
            include_trigger=True,
            db_function=False,
        )
