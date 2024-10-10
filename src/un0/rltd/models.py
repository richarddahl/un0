# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from sqlalchemy import UniqueConstraint, Identity, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from un0.db import Base, str_26, str_255  # type: ignore


class TableType(Base):
    """Table Types identify the tables in the database, similar to contenttypes in Django"""

    __tablename__ = "tabletype"
    __table_args__ = (
        UniqueConstraint("schema", "name", name="uq_tabletype_schema_name"),
        {
            "schema": "un0",
            "comment": "Table Types identify the tables in the database, similar to contenttypes in Django",
            "info": {"rls_policy": "superuser"},
        },
    )

    id: Mapped[int] = mapped_column(
        Identity(start=1, cycle=False),
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

    __tablename__ = "relatedobject"
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
        doc="Primary Key",
    )

    tabletype_id: Mapped[int] = mapped_column(
        ForeignKey("un0.tabletype.id", ondelete="CASCADE"),
        info={"edge": "HAS_tabletype"},
    )

    # Relationships
