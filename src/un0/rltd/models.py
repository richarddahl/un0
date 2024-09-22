# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import (
    ENUM,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from un0.fltr.enums import (  # type: ignore
    ColumnSecurity,
    Include,
    Match,
    FieldType,
    Lookup,
)
from un0.db import Base, BaseMixin, str_26, str_255  # type: ignore


class TableType(Base):
    """Table Types identify the tables in the database, similar to contenttypes in Django"""

    __tablename__ = "table_type"
    __table_args__ = (
        sa.UniqueConstraint("schema", "name", name="uq_table_type_schema_name"),
        {
            "schema": "un0",
            "comment": "Table Types identify the tables in the database, similar to contenttypes in Django",
            "info": {"rls_policy": "superuser"},
        },
    )

    id: Mapped[int] = mapped_column(
        sa.Identity(start=1, cycle=False),
        primary_key=True,
        index=True,
        doc="Primary Key",
    )
    schema: Mapped[str_255] = mapped_column(doc="Schema of the table")
    name: Mapped[str_255] = mapped_column(doc="Name of the table")

    # Relationships
    """
    # related_object: Mapped["RelatedObject"] = relationship(
    #    back_populates="table_type",
    #    foreign_keys="RelatedObject.table_type_id",
    #    doc="Related Object of the table",
    # )
    workflows: Mapped[list["Workflow"]] = relationship(
        back_populates="applicable_table_type",
        foreign_keys="Workflow.applicable_table_type_id",
        doc="Workflows applicable to the table",
    )
    object_functions: Mapped[list["ObjectFunction"]] = relationship(
        back_populates="table_type",
        doc="Object Functions of the table",
    )
    table_permissions: Mapped[list["TablePermission"]] = relationship(
        back_populates="table_type",
        doc="Permissions of the table",
    )
    fields: Mapped[list["Field"]] = relationship(
        back_populates="table_type",
        doc="Fields of the table",
    )
    source_filter_keys: Mapped[list["FilterKey"]] = relationship(
        back_populates="source",
        foreign_keys="FilterKey.source_id",
        doc="Source Filter Keys of the table",
    )
    destination_filter_keys: Mapped[list["FilterKey"]] = relationship(
        back_populates="destination",
        foreign_keys="FilterKey.destination_id",
        doc="Destination Filter Keys of the table",
    )
    """


class RelatedObject(Base):
    """Related Objects are used for the pk of all objects in the database,
    allowing for a single point of reference for queries, workflows, and reports
    """

    __tablename__ = "related_object"
    __table_args__ = {
        "schema": "un0",
        "comment": textwrap.dedent(
            """
            Related Objects are used for the pk of all objects in the database,
            allowing for a single point of reference for queries, workflows, and reports
            """
        ),
    }

    # Columns
    id: Mapped[str_26] = mapped_column(
        primary_key=True,
        nullable=False,
        index=True,
        server_default=sa.func.un0.generate_ulid(),
        doc="Primary Key",
    )

    table_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "HAS_TABLE_TYPE"},
    )

    # Relationships
    # table_type: Mapped["TableType"] = relationship(
    #    back_populates="related_object",
    #    foreign_keys="RelatedObject.table_type_id",
    # )
    # workflow_record: Mapped[list["WorkflowRecord"]] = relationship(
    #    back_populates="record",
    #    foreign_keys="WorkflowRecord.record_id",
    # )
    # workflow_event: Mapped[list["WorkflowEvent"]] = relationship(
    #    back_populates="workflow_object",
    #    foreign_keys="WorkflowEvent.object_id",
    # )
    # message_object: Mapped[list["MessageObject"]] = relationship(
    #    back_populates="object",
    #    foreign_keys="MessageObject.object_id",
    # )
    # filter_key: Mapped[list["FilterKey"]] = relationship(
    #    back_populates="related_object",
    #    foreign_keys="FilterKey.related_object_id",
    # )
    # filter_value: Mapped["FilterValue"] = relationship(
    #    back_populates="related_object",
    #    foreign_keys="FilterValue.related_object_id",
    # )
    # filter_object_values: Mapped[list["FilterValue"]] = relationship(
    #    back_populates="object_value",
    #    foreign_keys="FilterValue.object_value_id",
    #    doc="Filter Values Object Values",
    # )


class Field(Base, BaseMixin):
    __tablename__ = "field"
    __table_args__ = (
        sa.UniqueConstraint("table_type_id", "field_name"),
        {
            "schema": "un0",
            "comment": "Describes a column in a db table.",
            "info": {"rls_policy": "superuser"},
        },
    )

    # Columns
    table_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_OF_TABLE_TYPE"},
    )
    field_name: Mapped[str_255] = mapped_column()
    label: Mapped[str_255] = mapped_column()
    field_type: Mapped[FieldType] = mapped_column(
        ENUM(
            FieldType,
            name="fieldtype",
            create_type=True,
            schema="un0",
        ),
    )
    includes: Mapped[list[Include]] = mapped_column(
        ENUM(
            Include,
            name="include",
            create_type=True,
            schema="un0",
        )
    )
    matches: Mapped[list[Match]] = mapped_column(
        ENUM(
            Match,
            name="match",
            create_type=True,
            schema="un0",
        )
    )
    lookups: Mapped[list[Lookup]] = mapped_column(
        ENUM(
            Lookup,
            name="lookup",
            create_type=True,
            schema="un0",
        )
    )
    column_security: Mapped[ColumnSecurity] = mapped_column(
        ENUM(
            ColumnSecurity,
            name="columsecurity",
            create_type=True,
            schema="un0",
        ),
        default=ColumnSecurity.PUBLIC,
    )

    # Relationships
    """
    table_type: Mapped["TableType"] = relationship(back_populates="fields")
    filter_values: Mapped[list["FilterValue"]] = relationship(back_populates="fields")
    """


class ObjectFunction(Base, BaseMixin):
    __tablename__ = "object_function"
    __table_args__ = {
        "schema": "un0",
        "comment": "Functions that can be called by user-defined workflows and reports",
        "info": {"rls_policy": "superuser"},
    }
    # Columns

    label: Mapped[str] = mapped_column(doc="Label of the function")
    documentation: Mapped[Optional[str]] = mapped_column(
        doc="Documentation of the function"
    )
    name: Mapped[str] = mapped_column(doc="Name of the function")
    table_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_OF_TABLE_TYPE"},
    )
    # Relationships
    """
    table_type: Mapped[TableType] = relationship(
        back_populates="object_function", doc="Table Type of the function"
    )
    """
