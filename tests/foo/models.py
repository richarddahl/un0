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

from un0.db import Base, BaseMixin, str_26, str_255  # type: ignore
from un0.rltd.models import RelatedObject, TableType


class TestFoo(Base, BaseMixin):
    __tablename__ = "test_foo"
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
        doc="Name of the test_foo.",
    )
    description: Mapped[Optional[str_255]] = mapped_column(
        doc="Description of the test_foo.",
    )
    bar_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.test_bar.id", ondelete="CASCADE"),
        index=True,
        doc="Bar of the test_foo.",
        info={"edge": "HAS_BAR"},
    )


class TestBar(Base, BaseMixin):
    __tablename__ = "test_bar"
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
        doc="Name of the test_foo.",
    )
    description: Mapped[Optional[str_255]] = mapped_column(
        doc="Description of the test_foo.",
    )
    primary_baz_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.test_baz.id", ondelete="CASCADE"),
        index=True,
        doc="Primary Baz of the test_bar.",
        info={"edge": "HAS_PRIMARY_BAZ"},
    )


class TestBaz(Base, BaseMixin):
    __tablename__ = "test_baz"
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
        doc="Name of the test_foo.",
    )
    description: Mapped[Optional[str_255]] = mapped_column(
        doc="Description of the test_foo.",
    )


class TestFooBaz(Base):
    __tablename__ = "test_foo_baz"
    __table_args__ = (
        {
            "schema": "un0",
            "comment": "Just a FooBaz.",
            "info": {"rls_policy": False, "vertex": False},
        },
    )

    # Columns
    test_foo_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.test_foo.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="Foo of the foo_bar.",
        info={"edge": "HAS_FOO"},
    )
    test_baz_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.test_baz.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="Bar of the foo_baz.",
        info={"edge": "HAS_BAZ"},
    )


class TestBarBaz(Base):
    __tablename__ = "test_bar_baz"
    __table_args__ = (
        {
            "schema": "un0",
            "comment": "Just a BarBaz.",
            "info": {"rls_policy": False, "vertex": False},
        },
    )

    # Columns
    test_bar_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.test_bar.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="Bar of the bar_baz.",
        info={"edge": "HAS_BAR"},
    )
    test_baz_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.test_baz.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="Bar of the bar_baz.",
        info={"edge": "HAS_BAZ"},
    )
