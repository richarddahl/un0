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
    table_name: Optional[str] = None
    schema_name: Optional[str] = None

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
