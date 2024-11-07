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
    field_name: Optional[str] = None

    @abstractmethod
    def emit_sql(self) -> str:
        raise NotImplementedError

    def create_sql_trigger(
        self,
        function_name: str,
        timing: str = "BEFORE",
        operation: str = "UPDATE",
        for_each: str = "ROW",
        db_function: bool = True,
    ) -> str:
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
        if function_args and include_trigger is True:
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
    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Create the table_type record
            INSERT INTO un0.table_type (db_schema, name)
            VALUES ('{self.schema_name}', '{self.table_name}');
            """
        )


@dataclass
class RecordVersionAuditSQL(SQLEmitter):
    def emit_sql(self) -> str:
        return textwrap.dedent(
            f"""
            -- Enable auditing for the table
            SELECT audit.enable_tracking('{self.schema_name}.{self.table_name}'::regclass);
            """
        )


@dataclass
class HistoryTableAuditSQL(SQLEmitter):
    def emit_sql(self) -> str:
        return f"{self.emit_create_history_table_sql}\n{self.emit_create_history_function_and_trigger_sql}"

    def emit_create_history_table_sql(self) -> str:
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
