# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Any

from dataclasses import field
from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

from sqlalchemy import (
    Table,
    ForeignKey,
    Index,
    UniqueConstraint,
    CheckConstraint,
    Column,
)

from un0.database.graph import Edge
from un0.database.enums import ColumnSecurity
from un0.database.sql_emitters import SQLEmitter


@dataclass
class FKDefinition:
    target_column_name: str
    name: str | None = None
    ondelete: str = "CASCADE"
    onupdate: str | None = None
    edge_label: str | None = None
    reverse_edge_labels: list[str] = field(default_factory=list)

    def create_foreign_key(self) -> ForeignKey:
        """
        Creates a ForeignKey object with the specified column, ondelete, onupdate, and name attributes.

        Returns:
            ForeignKey: A ForeignKey object configured with the provided attributes.
        """

        return ForeignKey(
            self.target_column_name,
            ondelete=self.ondelete,
            onupdate=self.onupdate,
            name=self.name,
        )


@dataclass
class UniqueDefinition:
    """
    UniqueDefinition class represents a unique constraint in a database model.

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
class CheckDefinition:
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
class IndexDefinition:
    """
    IndexDefinition class represents an index with a name and a list of columns.

    Attributes:
        columns (list[str]): A list of column names that are part of the index.
        name (str | None): The name of the index. Defaults to None.

    Methods:
        create_index() -> Index:
            Creates and returns an Index object using the name and columns of the IndexDefinition instance.
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
class SuperUserColumnSecurityInsertSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
            BEGIN
                IF superuser THEN
                    NEW.{self.field_name} = NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} = NULL;
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_superuser_insert",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=False,
        )


@dataclass
class SuperUserColumnSecurityUpdateSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
            BEGIN
                IF superuser THEN
                    NEW.{self.field_name} := NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} := OLD.{self.field_name};
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_superuser_update",
            function_string,
            timing="BEFORE",
            operation="UPDATE",
            include_trigger=True,
            db_function=False,
        )


@dataclass
class AdminColumnSecurityInsertSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
                is_tenant_admin BOOLEAN := current_setting('rls_var.is_tenant_admin', true)::BOOLEAN;
            BEGIN
                IF is_superuser OR is_tenant_admin THEN
                    NEW.{self.field_name} = NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} = NULL;
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_admin_insert",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=False,
        )


@dataclass
class AdminColumnSecurityUpdateSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
                is_tenant_admin BOOLEAN := current_setting('rls_var.is_tenant_admin', true)::BOOLEAN;
            BEGIN
                IF is_superuser OR is_tenant_admin THEN
                    NEW.{self.field_name} := NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} := OLD.{self.field_name};
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_admin_update",
            function_string,
            timing="BEFORE",
            operation="UPDATE",
            include_trigger=True,
            db_function=False,
        )


@dataclass
class OwnerColumnSecurityInsertSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
                is_tenant_admin BOOLEAN := current_setting('rls_var.is_tenant_admin', true)::BOOLEAN;
                user_id TEXT := current_setting('rls_var.user_id', true)::TEXT;
            BEGIN
                IF is_superuser OR is_tenant_admin OR NEW.owned_by_id = user_id THEN
                    NEW.{self.field_name} = NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} = NULL;
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_owner_insert",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=False,
        )


@dataclass
class OwnerColumnSecurityUpdateSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = f"""
            DECLARE
                is_superuser BOOLEAN := current_setting('rls_var.is_superuser', true)::BOOLEAN;
                is_tenant_admin BOOLEAN := current_setting('rls_var.is_tenant_admin', true)::BOOLEAN;
                user_id TEXT := current_setting('rls_var.user_id', true)::TEXT;
            BEGIN
                IF is_superuser OR is_tenant_admin OR NEW.owned_by_id = user_id THEN
                    NEW.{self.field_name} := NEW.{self.field_name};
                ELSE
                    NEW.{self.field_name} := OLD.{self.field_name};
                END IF;
            RETURN NEW;
            END;
        """
        return self.create_sql_function(
            f"{self.field_name}_owner_update",
            function_string,
            timing="BEFORE",
            operation="UPDATE",
            include_trigger=True,
            db_function=False,
        )


@dataclass
class FieldDefinition:
    data_type: Any
    fnct: Any | None = None
    required: bool = False
    primary_key: bool = False
    index: bool = False
    unique: bool = False
    nullable: bool | None = None
    constraint_definitions: list[CheckDefinition | UniqueDefinition] = field(
        default_factory=list
    )
    foreign_key_definition: FKDefinition | None = None
    default: Any = None
    server_default: Any = None
    server_ondelete: Any = None
    server_onupdate: Any = None
    autoincrement: bool | str = False
    comment: str = ""
    info_dict: dict[str, Any] = field(default_factory=dict)

    # Graph related attributes
    edge_label: str | None = None
    reverse_edge_labels: list[str] = field(default_factory=list)

    # Security attributes
    select_permission: ColumnSecurity = ColumnSecurity.PUBLIC
    insert_permission: ColumnSecurity = ColumnSecurity.PUBLIC
    update_permission: ColumnSecurity = ColumnSecurity.PUBLIC

    include_in_masks: list[str] = field(
        default_factory=lambda: ["insert", "update", "select", "list"]
    )
    exclude_from_masks: list[str] = field(default_factory=list)
    editable: bool = True

    def create_column(self, name: str) -> Column:
        """
        Creates a SQLAlchemy Column object with the specified properties.

        Args:
            name (str): The name of the column.

        Returns:
            Column: A SQLAlchemy Column object configured with the specified properties.

        """
        args = [name, self.data_type]
        if self.fnct is not None:
            args.append(self.fnct)
        if self.foreign_key_definition is not None:
            args.append(self.foreign_key_definition.create_foreign_key())
            self.info_dict.update(
                {
                    "edge_label": self.foreign_key_definition.edge_label,
                    "reverse_edge_labels": self.foreign_key_definition.reverse_edge_labels,
                }
            )
        for constraint in self.constraint_definitions:
            args.append(constraint.create_constraint())

        kwargs = {
            "primary_key": self.primary_key,
            "index": self.index,
            "unique": self.unique,
            "server_default": self.server_default,
            "default": self.default,
            "doc": self.comment,
            "info": self.info_dict,
        }
        if self.nullable is not None:
            kwargs.update({"nullable": self.nullable})
        if self.autoincrement:
            kwargs.update({"autoincrement": self.autoincrement})
        if self.server_onupdate:
            kwargs.update({"server_onupdate": self.server_onupdate})

        if self.insert_permission == ColumnSecurity.SUPERUSER:
            self.sql_emitters.append(SuperUserColumnSecurityInsertSQL)
        elif self.insert_permission == ColumnSecurity.ADMIN:
            self.sql_emitters.append(AdminColumnSecurityInsertSQL)
        elif self.insert_permission == ColumnSecurity.OWNER:
            self.sql_emitters.append(OwnerColumnSecurityInsertSQL)

        if self.update_permission == ColumnSecurity.SUPERUSER:
            self.sql_emitters.append(SuperUserColumnSecurityUpdateSQL)
        elif self.update_permission == ColumnSecurity.ADMIN:
            self.sql_emitters.append(AdminColumnSecurityUpdateSQL)
        elif self.update_permission == ColumnSecurity.OWNER:
            self.sql_emitters.append(OwnerColumnSecurityUpdateSQL)

        return Column(*args, **kwargs)
