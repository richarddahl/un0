# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Any

from sqlalchemy import (
    Table,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
    Column,
)
from pydantic.dataclasses import dataclass
from dataclasses import field


@dataclass
class FK:
    """
    Represents a foreign key constraint in a database model.

    Attributes:
        target (str): The target table or column for the foreign key.
        name (str | None): The name of the foreign key constraint. Defaults to None.
        ondelete (str): The action to take when the target is deleted. Defaults to "CASCADE".
        onupdate (str | None): The action to take when the target is updated. Defaults to None.

    Methods:
        create_foreign_key() -> ForeignKey:
            Creates and returns a ForeignKey object based on the attributes of the FK instance.
    """

    target: str
    name: str | None = None
    ondelete: str = "CASCADE"
    onupdate: str | None = None
    to_edge: str | None = None
    from_edge: str | None = None

    def create_foreign_key(self) -> ForeignKey:
        """
        Creates a ForeignKey object with the specified target, ondelete, onupdate, and name attributes.

        Returns:
            ForeignKey: A ForeignKey object configured with the provided attributes.
        """
        # if self.to_edge is not None:
        #    create_to_edge = f"{self.from_edge} -> {self.to_edge}"
        # if self.from_edge is not None:
        #    create_to_edge = f"{self.from_edge} -> {self.target}"
        # else:
        #    Loop the table's fks and create from_edges for each

        return ForeignKey(
            self.target,
            ondelete=self.ondelete,
            onupdate=self.onupdate,
            name=self.name,
        )


@dataclass
class UQ:
    """
    UQ class represents a unique constraint in a database model.

    Attributes:
        columns (list[str]): A list of column names that the unique constraint applies to.
        name (str | None): The name of the unique constraint. Defaults to None.

    Methods:
        create_constraint() -> UniqueConstraint:
            Creates and returns a UniqueConstraint object based on the columns and name attributes.
    """

    columns: list[str]
    name: str | None = None

    def create_constraint(self) -> UniqueConstraint:
        """
        Creates a unique constraint for the specified columns.

        Returns:
            UniqueConstraint: An instance of UniqueConstraint with the specified columns and name.
        """
        return UniqueConstraint(*self.columns, name=self.name)


@dataclass
class CK:
    """
    A class representing a check constraint for a database model.

    Attributes:
        expression (str): The SQL expression for the check constraint.
        name (str | None): The optional name of the check constraint.

    Methods:
        create_constraint() -> CheckConstraint:
            Creates and returns a CheckConstraint object based on the expression and name attributes.
    """

    expression: str
    name: str | None = None

    def create_constraint(self) -> CheckConstraint:
        """
        Creates a CheckConstraint object with the specified expression and name.

        Returns:
            CheckConstraint: A new CheckConstraint object initialized with the
                             provided expression and name.
        """
        return CheckConstraint(self.expression, name=self.name)


@dataclass
class IX:
    """
    IX class represents an index with a name and a list of columns.

    Attributes:
        columns (list[str]): A list of column names that are part of the index.
        name (str | None): The name of the index. Defaults to None.

    Methods:
        create_index() -> Index:
            Creates and returns an Index object using the name and columns of the IX instance.
    """

    columns: list[str]
    name: str | None = None

    def create_index(self, table: Table) -> Index:
        """
        Creates and returns an Index object.

        This method constructs an Index object using the name and columns
        attributes of the instance.

        Returns:
            Index: The created Index object.
        """
        for column in self.columns:
            if column not in table.columns:
                raise ValueError(f"Column {column} not found in table {table.name}")
        cols = [table.c[column] for column in self.columns]

        return Index(self.name, *cols)


@dataclass
class FieldDefinition:
    data_type: Any
    fnct: Any | None = None
    required: bool = False
    primary_key: bool = False
    index: bool = False
    unique: bool = False
    nullable: bool | None = None
    constraints: list[CK | UQ] = field(default_factory=list)
    foreign_key: FK | None = None
    default: Any = None
    server_default: Any = None
    server_ondelete: Any = None
    server_onupdate: Any = None
    autoincrement: bool | str = False
    comment: str = ""
    column_security: str | None = None

    include_in_masks: list[str] = field(
        default_factory=lambda: ["insert", "update", "select", "list"]
    )
    exclude_in_masks: list[str] = field(default_factory=list)
    editable: bool = True

    def create_column(self, name: str) -> Column:
        """
        Creates a SQLAlchemy Column object with the specified attributes.

        Args:
            name (str): The name of the column.

        Returns:
            Column: A SQLAlchemy Column object configured with the specified attributes.
        """
        args = [name, self.data_type]
        if self.fnct is not None:
            args.append(self.fnct)
        if self.foreign_key is not None:
            args.append(self.foreign_key.create_foreign_key())
        for constraint in self.constraints:
            args.append(constraint.create_constraint())

        kwargs = {
            "primary_key": self.primary_key,
            "index": self.index,
            "unique": self.unique,
            "server_default": self.server_default,
            "default": self.default,
            "doc": self.comment,
        }
        if self.nullable is not None:
            kwargs.update({"nullable": self.nullable})
        if self.autoincrement:
            kwargs.update({"autoincrement": self.autoincrement})
        if self.server_onupdate:
            kwargs.update({"server_onupdate": self.server_onupdate})
        if name == "email":
            print(kwargs)
        return Column(*args, **kwargs)
