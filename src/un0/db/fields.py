# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Any

from sqlalchemy import (
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

    def create_foreign_key(self) -> ForeignKey:
        """
        Creates a ForeignKey object with the specified target, ondelete, onupdate, and name attributes.

        Returns:
            ForeignKey: A ForeignKey object configured with the provided attributes.
        """
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
        return UniqueConstraint(
            *self.columns,
            name=self.name,
        )


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
        return CheckConstraint(
            self.expression,
            name=self.name,
        )


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

    def create_index(self) -> Index:
        """
        Creates and returns an Index object.

        This method constructs an Index object using the name and columns
        attributes of the instance.

        Returns:
            Index: The created Index object.
        """
        return Index(
            self.name,
            *self.columns,
        )


@dataclass
class FieldDefinition:
    """
    A class used to define the properties and constraints of a database field.

    Attributes:
    ----------
    data_type : Any
        The data type of the field.
    required : bool, optional
        Indicates if the field is required (default is False).
    primary_key : bool, optional
        Indicates if the field is a primary key (default is False).
    index : bool, optional
        Indicates if the field should be indexed (default is False).
    unique : bool, optional
        Indicates if the field should have a unique constraint (default is False).
    nullable : bool, optional
        Indicates if the field can be null (default is True).
    constraints : list[CK | UQ], optional
        A list of constraints for the field (default is an empty list).
    foreign_key : FK | None, optional
        A foreign key constraint for the field (default is None).
    server_default : Any, optional
        The default value for the field on the server side (default is None).
    server_ondelete : Any, optional
        The action to take on delete on the server side (default is None).
    autoincrement : bool, optional
        Indicates if the field should auto-increment (default is False).
    comment : str, optional
        A comment for the field (default is an empty string).
    column_security : str | None, optional
        Security settings for the column (default is None).
    include_in_masks : list[str], optional
        A list of masks to include the field in (default is ["insert", "update", "select", "list"]).
    exclude_in_masks : list[str], optional
        A list of masks to exclude the field from (default is an empty list).
    exclude_from_graph : bool, optional
        Indicates if the field should be excluded from the graph (default is False).
    to_fk_edge_name : str | None, optional
        The name of the foreign key edge to (default is None).
    from_fk_edge_name : str | None, optional
        The name of the foreign key edge from (default is None).
    editable : bool, optional
        Indicates if the field is editable (default is True).

    Methods:
    -------
    create_column(name: str) -> Column:
        Creates a SQLAlchemy Column object based on the field definition.
    """

    data_type: Any
    required: bool = False
    primary_key: bool = False
    index: bool = False
    unique: bool = False
    nullable: bool = True
    constraints: list[CK | UQ] = field(default_factory=list)
    foreign_key: FK | None = None
    server_default: Any = None
    server_ondelete: Any = None
    autoincrement: bool = False
    comment: str = ""
    column_security: str | None = None

    include_in_masks: list[str] = field(
        default_factory=lambda: ["insert", "update", "select", "list"]
    )
    exclude_in_masks: list[str] = field(default_factory=list)
    exclude_from_graph: bool = False
    to_fk_edge_name: str | None = None
    from_fk_edge_name: str | None = None
    editable: bool = True

    def create_column(self, name: str) -> Column:
        """
        Creates a SQLAlchemy Column object with the specified attributes.

        Args:
            name (str): The name of the column.

        Returns:
            Column: A SQLAlchemy Column object configured with the specified attributes.
        """
        if self.foreign_key is not None:
            fk = self.foreign_key.create_foreign_key()
            return Column(
                self.data_type,
                fk,
                name=name,
                primary_key=self.primary_key,
                index=self.index,
                unique=self.unique,
                nullable=self.nullable,
                server_default=self.server_default,
                autoincrement=self.autoincrement,
                comment=self.comment,
            )
        return Column(
            self.data_type,
            name=name,
            primary_key=self.primary_key,
            index=self.index,
            unique=self.unique,
            nullable=self.nullable,
            server_default=self.server_default,
            autoincrement=self.autoincrement,
            comment=self.comment,
        )
