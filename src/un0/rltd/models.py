# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from un0.db import Base, str_26, str_255  # type: ignore


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
        doc="Primary Key",
    )

    table_type_id: Mapped[int] = mapped_column(
        sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "HAS_TABLE_TYPE"},
    )

    # Relationships
