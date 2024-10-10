# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import textwrap

from pydantic import BaseModel, computed_field
from sqlalchemy import Table

from un0.config import settings as sttngs


class UnoBaseSchema(BaseModel):
    """ """

    table: Table
    db_name: str = sttngs.DB_NAME
    # table_name: str <- computed_field
    # table_schema: str <- computed_field

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
        function_string: str,
        operation: str = "UPDATE",
        for_each: str = "ROW",
        include_trigger: bool = False,
    ) -> str:
        func_string = textwrap.dedent(
            f"CREATE OR REPLACE FUNCTION {self.table_schema}.{self.table_name}_{function_name}()\n"
            "RETURNS TRIGGER\n"
            "LANGUAGE plpgsql\n"
            "VOLATILE\n"
            "AS $BODY$\n"
            "BEGIN\n"
            f"    SET ROLE {self.db_name}_admin;\n"
            f"{textwrap.dedent(function_string)}\n"
            "END;\n"
            "$BODY$;\n"
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
        sql_str = (
            f"{textwrap.dedent(func_string)}\n{textwrap.dedent(trigger_string)}"
            if include_trigger
            else func_string
        )
        return textwrap.dedent(sql_str)
