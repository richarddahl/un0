# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime

from enum import Enum
from decimal import Decimal
from typing import Annotated, ClassVar, Type

from sqlalchemy import (
    MetaData,
    Table,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    registry,
)
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
)
from sqlalchemy.dialects.postgresql import (
    BIGINT,
    TIMESTAMP,
    DATE,
    TIME,
    VARCHAR,
    BOOLEAN,
    ENUM,
    NUMERIC,
    ARRAY,
)

from pydantic import BaseModel

from un0.errors import ModelRegistryError
from un0.utilities import convert_snake_to_title
from un0.db.sql_emitters import (
    SQLEmitter,
    BaseTableSQLEmitter,
)
from un0.db.fields import (
    IX,
    CK,
    UQ,
    FieldDefinition,
)
from un0.db.types import str_26, str_64, str_128, str_255, decimal
from un0.config import settings

# configures the naming convention for the database implicit constraints and indexes
POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}

# Creates the metadata object, used to define the database tables
meta_data = MetaData(
    naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION,
    schema=settings.DB_NAME,
)


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for SQLAlchemy models with asynchronous attributes and custom type annotations.

    Attributes:
        registry (sqlalchemy.orm.registry): A registry object that maps Python types to SQLAlchemy column types.
        metadata (sqlalchemy.MetaData): Metadata object for the database schema.

    Type Annotations:
        int: BIGINT
        datetime.datetime: TIMESTAMP(timezone=True)
        datetime.date: DATE
        datetime.time: TIME
        str: VARCHAR
        Enum: ENUM
        bool: BOOLEAN
        list: ARRAY
        str_26: VARCHAR(26)
        str_64: VARCHAR(64)
        str_128: VARCHAR(128)
        str_255: VARCHAR(255)
        decimal: NUMERIC
    """

    registry = registry(
        type_annotation_map=(
            {
                int: BIGINT,
                datetime.datetime: TIMESTAMP(timezone=True),
                datetime.date: DATE,
                datetime.time: TIME,
                str: VARCHAR,
                Enum: ENUM,
                bool: BOOLEAN,
                list: ARRAY,
                str_26: VARCHAR(26),
                str_64: VARCHAR(64),
                str_128: VARCHAR(128),
                str_255: VARCHAR(255),
                decimal: NUMERIC,
            }
        )
    )
    metadata = meta_data


class Model(BaseModel):
    """
    Model is a base class for defining database models with SQLAlchemy. It provides mechanisms for
    automatically generating and registering table schemas, field definitions, constraints, and indices.
    The class also supports emitting SQL statements for table creation.

    Attributes:
        table (ClassVar[Table]): The SQLAlchemy Table object associated with the model.
        registry (ClassVar[dict[str, Model]]): A registry mapping table names to model classes.
        class_name_map (ClassVar[dict[str, str]]): A mapping of class names to table names.
        db_schema (ClassVar[str]): The database schema name.
        table_name (ClassVar[str]): The name of the table.
        table_name_plural (ClassVar[str]): The plural form of the table name.
        verbose_name (ClassVar[str]): A human-readable name for the table.
        verbose_name_plural (ClassVar[str]): A human-readable plural name for the table.
        table_comment (ClassVar[str]): A comment describing the table.
        field_definitions (ClassVar[dict[str, "FieldDefinition"]]): Definitions of the fields in the table.
        indices (ClassVar[list[IX]]): A list of indices for the table.
        constraints (ClassVar[list[CK | UQ]]): A list of constraints for the table.
        sql_emitters (ClassVar[list[SQLEmitter]]): A list of SQL emitters for generating SQL statements.

    Methods:
        __init_subclass__: Initializes a subclass, setting up table attributes and registering the class.
        update_field_definitions: Updates the field definitions by merging those from parent classes.
        update_constraints: Updates the constraints by extending those from parent classes.
        update_indices: Updates the indices by extending those from parent classes.
        emit_sql: Generates and returns SQL statements emitted by all associated SQL emitters.
    """

    table: ClassVar[Table]

    registry: ClassVar[dict[str, "Model"]] = {}
    class_name_map: ClassVar[dict[str, str]] = {}

    db_schema: ClassVar[str]
    table_name: ClassVar[str]
    table_name_plural: ClassVar[str]
    verbose_name: ClassVar[str]
    verbose_name_plural: ClassVar[str]
    table_comment: ClassVar[str] = ""
    field_definitions: ClassVar[dict[str, "FieldDefinition"]] = {}
    indices: ClassVar[list[IX]] = []
    constraints: ClassVar[list[CK | UQ]] = []
    sql_emitters: ClassVar[list[SQLEmitter]] = [BaseTableSQLEmitter]

    def __init_subclass__(
        cls,
        db_schema: str | None = settings.DB_NAME,
        table_name: str | None = None,
        table_name_plural: str | None = None,
        verbose_name: str | None = None,
        verbose_name_plural: str | None = None,
    ) -> None:
        """
        Initialize a subclass of the Model class.

        This method is automatically called when a new subclass is created. It sets up
        various class attributes and ensures the subclass is properly registered.

        Args:
            cls: The subclass being initialized.
            db_schema (str | None): The database schema name. Defaults to the value of settings.DB_NAME.
            table_name (str | None): The name of the table. Defaults to None.
            table_name_plural (str | None): The plural name of the table. Defaults to None.
            verbose_name (str | None): A human-readable name for the table. Defaults to None.
            verbose_name_plural (str | None): A human-readable plural name for the table. Defaults to None.

        Raises:
            ModelRegistryError: If a class with the same table name or model name already exists in the registry.

        Notes:
            - This method prevents the base class from being created and added to the registry.
            - It updates field definitions, constraints, and indices from the parent classes.
            - It sets various class attributes such as table_name, db_schema, table_name_plural, verbose_name, and verbose_name_plural.
            - It ensures the subclass is added to the registry only once.
            - It creates the SQLAlchemy table object and adds columns, constraints, and indices to it.
        """

        # This prevents the base class from being created and added to the registry
        if isinstance(cls, Model):
            return

        # Update the field_definitions, constraints, and indices from the parent classes
        cls.update_field_definitions()
        cls.update_constraints()
        cls.update_indices()

        # Set the class attributes
        cls.table_name = table_name
        cls.db_schema = db_schema
        cls.table_name_plural = (
            f"{table_name}s" if table_name_plural is None else table_name_plural
        )
        cls.verbose_name = (
            convert_snake_to_title(table_name) if verbose_name is None else verbose_name
        )
        cls.verbose_name_plural = (
            convert_snake_to_title(cls.table_name_plural)
            if verbose_name_plural is None
            else verbose_name_plural
        )

        # This is here as we only want to create and add the class to the registry once
        # The BaseClass registry is shared by all subclasses
        # It's like a singleton, it exists in the base class and is shared by all subclasses
        if cls.table_name not in cls.registry:
            # Add the subclass to the table_name_registry
            cls.registry.update({cls.table_name: cls})
            # Add the subclass to the model_name_registry if it is not there (shouldn't be there, but just in case)
            if cls.__name__ not in cls.class_name_map:
                cls.class_name_map.update({cls.__name__: cls})
            else:
                raise ModelRegistryError(
                    f"A class with the table name {cls.table_name} already exists.",
                    "MODEL_NAME_EXISTS_IN_REGISTRY",
                )
        else:
            raise ModelRegistryError(
                f"A class with the table name {cls.table_name} already exists.",
                "TABLE_NAME_EXISTS_IN_REGISTRY",
            )

        # Create the sqlalchemy table object
        table = Table(
            cls.table_name,
            Base.metadata,
            schema=cls.db_schema,
            comment=cls.table_comment,
        )
        # Add the columns to the table
        for field_name, field_definition in cls.field_definitions.items():
            table.append_column(field_definition.create_column(name=field_name))
        # Add the constraints to the table
        for constraint in cls.constraints:
            table.append_constraint(constraint.create_constraint())
        # Add the indices to the table
        for index in cls.indices:
            table.indexes.add(index.create_index())
        # Set the table attribute on the class
        cls.table = table

    @classmethod
    def update_field_definitions(cls) -> None:
        """
        Updates the `field_definitions` attribute of the class by iterating through
        the method resolution order (MRO) of the class and merging the `field_definitions`
        from each class in the hierarchy.

        This method ensures that the `field_definitions` attribute contains all field
        definitions from the current class and its ancestors.

        Returns:
            None
        """
        for klass in cls.__class__.mro(cls):
            if hasattr(klass, "field_definitions"):
                cls.field_definitions.update(klass.field_definitions)

    @classmethod
    def update_constraints(cls) -> None:
        """
        Updates the constraints of the class by extending the current class's
        constraints with those of its parent classes.

        This method iterates through the method resolution order (MRO) of the
        class and checks if each class in the hierarchy has a 'constraints'
        attribute. If it does, the constraints of the current class are extended
        with the constraints of that class.

        Returns:
            None
        """
        for klass in cls.__class__.mro(cls):
            if hasattr(klass, "constraints"):
                cls.constraints.extend(klass.constraints)

    @classmethod
    def update_indices(cls) -> None:
        """
        Updates the indices of the class by extending the current class's indices
        with the indices of all its parent classes in the method resolution order (MRO).

        This method iterates through the MRO of the class and checks if each class
        has an attribute named 'indices'. If the attribute exists, it extends the
        current class's indices with the indices of that class.

        Returns:
            None
        """
        for klass in cls.__class__.mro(cls):
            if hasattr(klass, "indices"):
                cls.indices.extend(klass.indices)

    @classmethod
    def emit_sql(cls) -> str:
        """
        Generates and returns the SQL statements emitted by all SQL emitters associated with the class.

        Returns:
            str: A string containing the concatenated SQL statements emitted by each SQL emitter.
        """
        emitted_sql = ""
        for sql_emitter in cls.sql_emitters:
            emitted_sql += f"{sql_emitter(table_name=cls.table_name, db_schema=cls.db_schema).emit_sql()}\n"
        return emitted_sql
