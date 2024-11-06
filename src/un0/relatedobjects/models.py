# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from typing import Optional

from sqlalchemy import Integer, Identity
from sqlalchemy.dialects.postgresql import TEXT, VARCHAR

from pydantic import computed_field
from pydantic.dataclasses import dataclass

from un0.database.fields import FK, UQ, FieldDefinition
from un0.database.models import Model
from un0.database.sql_emitters import SQLEmitter
from un0.authorization.sql_emitters import InsertTableOperationFnctnTrggrSQL


class TableType(
    Model,
    schema_name="un0",
    table_name="table_type",
):
    sql_emitters = [InsertTableOperationFnctnTrggrSQL]
    constraints = [
        UQ(
            columns=["db_schema", "name"],
            name="uq_tabletype_db_schema_name",
        )
    ]
    field_definitions = {
        "id": FieldDefinition(
            data_type=Integer,
            fnct=Identity(start=1, cycle=False),
            primary_key=True,
            index=True,
            doc="Primary Key",
        ),
        "db_schema": FieldDefinition(
            data_type=TEXT,
            nullable=False,
            index=True,
            doc="Name of the tables schema_name",
        ),
        "name": FieldDefinition(
            data_type=TEXT,
            nullable=False,
            index=True,
            doc="Name of the table",
        ),
    }

    id: Optional[int] = None
    db_schema: Optional[str] = None
    name: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.db_schema}.{self.name}"


@dataclass
class InsertRelatedObjectFnctnSQL(SQLEmitter):
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

        return self.create_sql_function("insert_related_object", function_string)


class RelatedObject(
    Model,
    schema_name="un0",
    table_name="related_object",
):
    sql_emitters = [InsertRelatedObjectFnctnSQL]
    field_definitions = {
        "id": FieldDefinition(
            data_type=VARCHAR(26),
            primary_key=True,
            index=True,
            doc="Primary Key",
        ),
        "table_type_id": FieldDefinition(
            data_type=Integer,
            foreign_key=FK(
                target="un0.table_type.id",
                ondelete="CASCADE",
            ),
            nullable=False,
            index=True,
            doc="The Table Type to which the related object refers",
            to_edge="HAS_TABLE_TYPE",
            from_edge="HAS_RELATED_OBJECT",
        ),
    }

    id: Optional[str] = None
    table_type_id: Optional[int] = None
    table_type: Optional[TableType] = None

    def __str__(self) -> str:
        return f"{self.table_type_id}"

    @computed_field
    def obj(self) -> Model:
        return self.TableType.db.get(id=self.id)
