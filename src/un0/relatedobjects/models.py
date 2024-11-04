# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Optional

from sqlalchemy import Integer, Identity
from sqlalchemy.dialects.postgresql import TEXT, VARCHAR

from pydantic import computed_field

from un0.database.fields import FK, UQ, FieldDefinition
from un0.database.models import Model
from un0.relatedobjects.sql_emitters import RelatedObjectIDFnctnSQL


class TableType(
    Model,
    schema_name="un0",
    table_name="table_type",
):
    """
    TableType Model

    This model represents the types of tables in the database, similar to contenttypes in Django.

    Attributes:
        id (Optional[int]): Primary key, auto-incremented.
        schema_name (Optional[str]): Name of the database schema_name.
        table_name (Optional[str]): Name of the table.

    Constraints:
        - Unique constraint on the combination of schema_name and table_name.

    SQL Emitters:
        - BaseTableSQLEmitter
        - DefaultAuditSQLEmitter

    Field Definitions:
        - id: Identity field, primary key, auto-incremented.
        - schema_name: String field, non-nullable, indexed.
        - table_name: String field, non-nullable, indexed.

    Methods:
        - __str__: Returns a string representation of the table in the format "schema_name.table_name".
    """

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


class RelatedObject(
    Model,
    schema_name="un0",
    table_name="related_object",
):
    """
    RelatedObject Model

    Related Objects are used for the primary key of many objects in the database,
    allowing for a single point of reference for attributes, queries, workflows, and reports.

    Attributes:
        id (Optional[str]): Primary Key.
        table_type_id (Optional[int]): The Table Type to which the related object refers.

    Field Definitions:
        id: FieldDefinition for the primary key.
        table_type_id: FieldDefinition for the foreign key referencing `un0.table_type.id`.

    Methods:
        obj() -> Model: Fetches the object from the database to which the related_object refers.
    """

    sql_emitters = [RelatedObjectIDFnctnSQL]
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

    @computed_field
    def obj(self) -> Model:
        """
        Fetches the object from the database to which the related_object refers.

        Returns:
            Model: The object fetched from the database.
        """
        return self.TableType.db.get(id=self.id)
