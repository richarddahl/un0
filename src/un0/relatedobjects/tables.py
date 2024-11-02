# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from sqlalchemy import UniqueConstraint, ForeignKey, Identity
from sqlalchemy.orm import Mapped, mapped_column

from un0.database.base import Base, str_26, str_255


class TableType(Base):
    """Table Types identify the tables in the database, similar to contenttypes in Django"""

    __tablename__ = "table_type"
    __table_args__ = (
        UniqueConstraint("schema_name", "name", name="uq_tabletype_schema_name"),
        {
            "schema_name": "un0",
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
    schema_name: Mapped[str_255] = mapped_column(doc="Schema of the table")
    name: Mapped[str_255] = mapped_column(doc="Name of the table")


class RelatedObject(Base):
    """Related Objects are used for the pk of many objects in the database,
    allowing for a single point of reference for attributes, queries, workflows, and reports
    """

    __tablename__ = "related_object"
    __table_args__ = {
        "schema_name": "un0",
        "comment": textwrap.dedent(
            """
            Related Objects are used for the pk of many objects in the database,
            allowing for a single point of reference for attributes, queries, workflows, and reports
            """
        ),
    }

    # Columns
    id: Mapped[str_26] = mapped_column(
        primary_key=True,
        doc="Primary Key",
    )
    table_type_id: Mapped[int] = mapped_column(
        ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        info={"edge": "HAS_TABLETYPE"},
    )
