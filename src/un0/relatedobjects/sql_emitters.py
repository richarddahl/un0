# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from pydantic.dataclasses import dataclass

from un0.database.sql_emitters import SQLEmitter
from un0.config import settings


@dataclass
class RelatedObjectIDFnctnSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = textwrap.dedent(
            """
            DECLARE
                table_type_id INT;
                related_object_id VARCHAR(26) := un0.generate_ulid();
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
                VALUES (related_object_id, table_type_id);
                NEW.id := related_object_id;
                RETURN NEW;
            END;
            """
        )

        return self.create_sql_function("set_related_object_id", function_string)


@dataclass
class SetRelatedObjectIDSQL(SQLEmitter):
    """ """

    def emit_sql(self) -> str:
        return self.create_sql_trigger(
            "set_related_object_id", timing="BEFORE", operation="INSERT"
        )
