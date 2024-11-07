# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from typing import Optional

from sqlalchemy.dialects.postgresql import VARCHAR

from pydantic.dataclasses import dataclass

from un0.database.models import Model
from un0.database.mixins import FieldMixin
from un0.database.fields import FieldDefinition, FK
from un0.database.sql_emitters import SQLEmitter


@dataclass
class InsertRelatedObjectSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = """
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

        return self.create_sql_function(
            "insert_related_object",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=True,
        )


class RelatedObjectIdMixin(FieldMixin):
    """ """

    sql_emitters = [InsertRelatedObjectSQL]

    field_definitions = {
        "id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key=FK(
                target="un0.related_object.id",
                ondelete="CASCADE",
                to_edge="HAS_ID",
                from_edge="IS_ID_OF",
            ),
            primary_key=True,
            index=True,
            unique=True,
            nullable=False,
            doc="Primary Key",
        ),
    }

    id: Optional[str] = None
    related_object: Optional[Model] = None
