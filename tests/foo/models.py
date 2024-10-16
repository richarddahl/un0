# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime
from typing import Optional

from sqlalchemy import (
    ForeignKey,
    Identity,
)

from sqlalchemy.orm import relationship, mapped_column, Mapped

from un0.db.base import Base, BaseMixin, str_26, str_255  # type: ignore
from un0.rltd.models import RelatedObject, TableType


class TestFoo(Base, BaseMixin):
    __tablename__ = "testfoo"
    __table_args__ = (
        {
            "schema": "un0",
            "comment": "Just a Foo.",
            "info": {"rls_policy": False},
        },
    )

    # Columns
    id: Mapped[int] = mapped_column(
        Identity(start=1, cycle=False),
        primary_key=True,
        index=True,
        doc="Primary Key",
    )
    name: Mapped[str_255] = mapped_column(
        doc="Name of the testfoo.",
    )
    description: Mapped[Optional[str_255]] = mapped_column(
        doc="Description of the testfoo.",
    )
    bar_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.testbar.id", ondelete="CASCADE"),
        index=True,
        doc="Bar of the testfoo.",
        info={"edge": "HAS_BAR"},
    )


class TestBar(Base, BaseMixin):
    __tablename__ = "testbar"
    __table_args__ = (
        {
            "schema": "un0",
            "comment": "Just a Bar.",
            "info": {"rls_policy": False},
        },
    )

    # Columns
    id: Mapped[int] = mapped_column(
        Identity(start=1, cycle=False),
        primary_key=True,
        index=True,
        doc="Primary Key",
    )
    name: Mapped[str_255] = mapped_column(
        doc="Name of the testfoo.",
    )
    description: Mapped[Optional[str_255]] = mapped_column(
        doc="Description of the testfoo.",
    )
    primary_baz_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.testbaz.id", ondelete="CASCADE"),
        index=True,
        doc="Primary Baz of the testbar.",
        info={"edge": "HAS_PRIMARY_BAZ"},
    )


class TestBaz(Base, BaseMixin):
    __tablename__ = "testbaz"
    __table_args__ = (
        {
            "schema": "un0",
            "comment": "Just a Baz.",
            "info": {"rls_policy": False},
        },
    )

    # Columns
    id: Mapped[int] = mapped_column(
        Identity(start=1, cycle=False),
        primary_key=True,
        index=True,
        doc="Primary Key",
    )
    name: Mapped[str_255] = mapped_column(
        doc="Name of the testfoo.",
    )
    description: Mapped[Optional[str_255]] = mapped_column(
        doc="Description of the testfoo.",
    )


class TestFooBaz(Base):
    __tablename__ = "testfoo_baz"
    __table_args__ = (
        {
            "schema": "un0",
            "comment": "Just a FooBaz.",
            "info": {"rls_policy": False, "vertex": False},
        },
    )

    # Columns
    testfoo_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.testfoo.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="Foo of the foo_bar.",
        info={"edge": "HAS_FOO"},
    )
    testbaz_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.testbaz.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="Bar of the foo_baz.",
        info={"edge": "HAS_BAZ"},
    )


class TestBarBaz(Base):
    __tablename__ = "testbar_baz"
    __table_args__ = (
        {
            "schema": "un0",
            "comment": "Just a BarBaz.",
            "info": {"rls_policy": False, "vertex": False},
        },
    )

    # Columns
    testbar_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.testbar.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="Bar of the bar_baz.",
        info={"edge": "HAS_BAR"},
    )
    testbaz_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.testbaz.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="Bar of the bar_baz.",
        info={"edge": "HAS_BAZ"},
    )
