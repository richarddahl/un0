# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Optional

from sqlalchemy import Integer, Identity
from sqlalchemy.dialects.postgresql import TEXT, VARCHAR

from pydantic import computed_field

from un0.database.fields import (
    FKDefinition,
    UniqueDefinition,
    FieldDefinition,
)
from un0.database.models import Model
from un0.authorization.sql_emitters import InsertTableOperation


class TableType(
    Model,
    schema_name="un0",
    table_name="table_type",
):
    sql_emitters = [InsertTableOperation]
    constraint_definitions = [
        UniqueDefinition(
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


class RelatedObject(
    Model,
    schema_name="un0",
    table_name="related_object",
):
    field_definitions = {
        "id": FieldDefinition(
            data_type=VARCHAR(26),
            primary_key=True,
            index=True,
            doc="Primary Key",
        ),
        "table_type_id": FieldDefinition(
            data_type=Integer,
            foreign_key_definition=FKDefinition(
                target_column_name="un0.table_type.id",
                ondelete="CASCADE",
                edge_label="HAS_TABLE",
                reverse_edge_labels=["IS_TABLE_OF"],
            ),
            nullable=False,
            index=True,
            doc="The Table Type to which the related object refers",
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
