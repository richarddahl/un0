# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
from enum import Enum

from typing import Type, ClassVar

from pydantic import BaseModel
from pydantic.dataclasses import dataclass, Field

from sqlalchemy import Table

from un0.errors import ModelRegistryError
from un0.utilities import convert_snake_to_title
from un0.database.base import metadata, Base
from un0.database.fields import (
    IndexDefinition,
    CheckDefinition,
    UniqueDefinition,
    FieldDefinition,
)
from un0.database.masks import Mask, MaskDef
from un0.database.enums import Cardinality, MaskType, SQLOperation
from un0.database.routers import RouterDef, Router
from un0.database.graph import Vertex, Edge, Property, Path
from un0.database.sql_emitters import (
    SQLEmitter,
    InsertTableTypeSQL,
    AlterGrantSQL,
)
from un0.config import settings


@dataclass
class RelatedModel:
    source: Type["Model"]
    cardinality: Cardinality = Cardinality.MANY_TO_ONE
    models: list[Type["Model"]] = Field(default_factory=list)


@dataclass
class ModelMixin:
    """
    A mixin class that provides common functionality for database models.
    Used to add common attributes to database models.

    Attributes:
        field_definitions (ClassVar[dict[str, FieldDefinition]]): A dictionary mapping field names
            to their definitions.
        index_definitions (ClassVar[list[IndexDefinition]]): A list of index definitions for the model.
        constraint_definitions (ClassVar[list[CheckDefinition | UniqueDefinition]]): A list of constraint
            definitions for the model, including check and unique constraints.
        sql_emitters (ClassVar[list[SQLEmitter]]): A list of SQL emitters associated with the model.

    Methods:
        emit_sql() -> str:
            Emits the SQL representation of the model.
    """

    field_definitions: ClassVar[dict[str, FieldDefinition]] = {}
    index_definitions: ClassVar[list[IndexDefinition]] = []
    constraint_definitions: ClassVar[list[CheckDefinition | UniqueDefinition]] = []
    sql_emitters: ClassVar[list[SQLEmitter]] = []

    def emit_sql(self) -> str:
        return super().emit_sql()


class Model(BaseModel, ModelMixin):
    """
    Model class that serves as a base for all database models in the application.

    Attributes:
        table (ClassVar[Table]): SQLAlchemy Table object associated with the model.
        registry (ClassVar[dict[str, "Model"]]): Registry of all model classes by table name.
        class_name_map (ClassVar[dict[str, str]]): Mapping of class names to their string representations.
        schema_name (ClassVar[str]): Name of the database schema.
        table_name (ClassVar[str]): Name of the database table.
        table_name_plural (ClassVar[str]): Plural name of the database table.
        verbose_name (ClassVar[str]): Human-readable name of the model.
        verbose_name_plural (ClassVar[str]): Plural human-readable name of the model.
        table_comment (ClassVar[str]): Comment for the database table.
        field_definitions (ClassVar[dict[str, FieldDefinition]]): Definitions of fields in the model.
        index_definitions (ClassVar[list[IndexDefinition]]): Definitions of indices for the model.
        constraint_definitions (ClassVar[list[CheckDefinition | UniqueDefinition]]): Definitions of constraints for the model.
        sql_emitters (ClassVar[list[str, Type[SQLEmitter]]]): List of SQL emitters for the model.
        related_models (ClassVar[dict[str, Type[RelatedModel]]]): Related models for the model.
        vertex_column (ClassVar[str]): Name of the vertex column.
        vertex (ClassVar[Vertex]): Vertex object associated with the model.
        properties (ClassVar[dict[str, Property]]): Properties of the model.
        edges (ClassVar[dict[str, Edge]]): Edges of the model.
        paths (ClassVar[dict[str, Path]]): Paths of the model.
        routers (ClassVar[list[Router]]): List of routers for the model.
        router_defs (ClassVar[dict[str, RouterDef]]): Definitions of routers for the model.
        masks (ClassVar[dict[str, Mask]]): Masks for the model.
        mask_defs (ClassVar[list[MaskDef]]): Definitions of masks for the model.

    Methods:
        __init_subclass__(cls, schema_name: str, table_name: str, table_name_plural: str | None = None, verbose_name: str | None = None, verbose_name_plural: str | None = None) -> None:
            Initializes a subclass of Model with the given schema and table names.

        update_field_definitions(cls) -> None:
            Updates the field definitions of the class by merging the field definitions from its ancestors.

        update_constraints(cls) -> None:
            Updates the constraints of the class by extending the current class's constraints with those of its parent classes.

        update_indices(cls) -> None:
            Updates the index definitions of the class by extending the current class's index definitions with those of its parent classes.

        update_sql_emitters(cls) -> None:
            Updates the SQL emitters of the class by extending the current class's SQL emitters with those of its parent classes.

        create_routers(cls) -> None:
            Creates routers for the model based on the router definitions.

        emit_sql(cls) -> str:
            Emits the SQL for the model, including vertex and SQL emitters.

        process_app_logic(self):
            Placeholder method for processing application logic.
    """

    table: ClassVar[Table]

    registry: ClassVar[dict[str, "Model"]] = {}
    class_name_map: ClassVar[dict[str, str]] = {}

    schema_name: ClassVar[str]
    table_name: ClassVar[str]
    table_name_plural: ClassVar[str]
    verbose_name: ClassVar[str]
    verbose_name_plural: ClassVar[str]
    table_comment: ClassVar[str] = ""
    field_definitions: ClassVar[dict[str, FieldDefinition]] = {}
    index_definitions: ClassVar[list[IndexDefinition]] = []
    constraint_definitions: ClassVar[list[CheckDefinition | UniqueDefinition]] = []
    sql_emitters: ClassVar[list[str, Type[SQLEmitter]]] = [
        AlterGrantSQL,
        InsertTableTypeSQL,
    ]
    related_models: ClassVar[dict[str, Type[RelatedModel]]] = {}

    # Graph related attributes
    vertex_column: ClassVar[str] = "id"
    vertex: ClassVar[Vertex] = None
    properties: ClassVar[dict[str, Property]] = {}
    edges: ClassVar[dict[str, Edge]] = {}
    paths: ClassVar[dict[str, Path]] = {}

    # Router related attributes
    routers: ClassVar[list[Router]] = []
    router_defs: ClassVar[dict[str, RouterDef]] = {
        "Insert": RouterDef(
            method="POST",
            endpoint="post",
        ),
        "List": RouterDef(
            method="GET",
            endpoint="get",
            multiple=True,
        ),
        "Update": RouterDef(
            path_suffix="{id}",
            method="PUT",
            endpoint="put",
        ),
        "Select": RouterDef(
            path_suffix="{id}",
            method="GET",
            endpoint="get_by_id",
        ),
        "Delete": RouterDef(
            path_suffix="{id}",
            method="DELETE",
            endpoint="delete",
        ),
    }
    masks: ClassVar[dict[str, Mask]] = {}
    mask_defs: ClassVar[list[MaskDef]] = [
        MaskDef(
            mask_type=MaskType.NATIVE,
            operation=[SQLOperation.SELECT],
        ),
        MaskDef(
            name="List",
            mask_type=MaskType.NATIVE,
            operation=[SQLOperation.SELECT],
        ),
        MaskDef(
            mask_type=MaskType.NATIVE,
            operation=[SQLOperation.INSERT],
        ),
        MaskDef(
            mask_type=MaskType.NATIVE,
            operation=[SQLOperation.UPDATE],
        ),
    ]

    def __init_subclass__(
        cls,
        schema_name: str,
        table_name: str,
        table_name_plural: str | None = None,
        verbose_name: str | None = None,
        verbose_name_plural: str | None = None,
    ) -> None:
        """
        Initialize a subclass of the Model class.

        This method is called when a class is subclassed from the Model class. It sets up
        various class attributes and registers the subclass in the model registry.

        Args:
            cls: The subclass being initialized.
            schema_name (str): The name of the schema to which the table belongs.
            table_name (str): The name of the table.
            table_name_plural (str, optional): The plural name of the table. Defaults to None.
            verbose_name (str, optional): A human-readable name for the table. Defaults to None.
            verbose_name_plural (str, optional): A human-readable plural name for the table. Defaults to None.

        Raises:
            ValueError: If `table_name` or `schema_name` is None.
            ModelRegistryError: If a class with the same table name or class name already exists in the registry.

        Returns:
            None
        """

        # This prevents the base class from being created and added to the registry
        if cls is Model:
            return

        # Set the class attributes
        # Set the class attributes for table and schema names
        if table_name is None:
            raise ValueError("table_name cannot be None")
        if schema_name is None:
            raise ValueError("schema_name cannot be None")
        cls.table_name = table_name
        cls.schema_name = schema_name
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
        # Add the subclass to the model_name_registry if it is not there (shouldn't be there, but just in case)
        if cls.__name__ not in cls.class_name_map:
            cls.class_name_map.update({cls.__name__: cls})
        else:
            raise ModelRegistryError(
                f"A class with the table name {cls.table_name} already exists.",
                "MODEL_NAME_EXISTS_IN_REGISTRY",
            )
        # Add the subclass to the table_name_registry
        if cls.table_name not in cls.registry:
            cls.registry.update({cls.table_name: cls})
        else:
            # Raise an error if a class with the same table name already exists in the registry
            raise ModelRegistryError(
                f"A class with the table name {cls.table_name} already exists.",
                "TABLE_NAME_EXISTS_IN_REGISTRY",
            )

        # Update the field_definitions, constraints, and index_definitions from the parent classes
        cls.update_field_definitions()
        cls.update_constraints()
        cls.update_indices()
        cls.update_sql_emitters()

        # Create and add columns to the SQLAlchemy table object
        columns = []
        # Add the columns to the table
        for field_name, field_definition in cls.field_definitions.items():
            columns.append(field_definition.create_column(name=field_name))

        constraints = []
        # Add the constraints to the table
        for constraint in cls.constraint_definitions:
            constraints.append(constraint.create_constraint())

        # Create the sqlalchemy table object
        table = Table(
            cls.table_name,
            Base.metadata,
            schema=cls.schema_name,
            comment=cls.table_comment,
            *columns,
            *constraints,
        )
        # Add the index_definitions to the table
        # Indices are added to improve the performance of database operations
        for index in cls.index_definitions:
            table.indexes.add(index.create_index(table))

        # Set the table attribute on the class to the created SQLAlchemy table object
        # cls.table = table
        cls.table = type(cls.table_name, (Base,), {"__table__": table})
        properties = {}
        for column in table.columns:
            properties[column.name] = Property(
                table_name=table.name, schema_name=table.schema, column=column
            )
        cls.properties = properties

        # if cls.vertex_column:
        #    cls.vertex = Vertex(
        #        table=cls.table,
        #        table_name=cls.table_name,
        #        schema_name=cls.schema_name,
        #        column_name=cls.vertex_column,
        #        properties=cls.properties,
        #    )

        cls.create_routers()

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
        field_definitions = {}
        for kls in cls.mro():
            if hasattr(kls, "field_definitions"):
                field_definitions.update(kls.field_definitions)
        cls.field_definitions = field_definitions

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
        for kls in cls.mro():
            if hasattr(kls, "constraint_definitions"):
                for constraint in kls.constraint_definitions:
                    if constraint not in cls.constraint_definitions:
                        cls.constraint_definitions.append(kls.constraint_definitions)

    @classmethod
    def update_indices(cls) -> None:
        """
        Updates the index_definitions of the class by extending the current class's index_definitions
        with the index_definitions of all its parent classes in the method resolution order (MRO).

        This method iterates through the MRO of the class and checks if each class
        has an attribute named 'index_definitions'. If the attribute exists, it extends the
        current class's index_definitions with the index_definitions of that class.

        Returns:
            None
        """
        for kls in cls.mro():
            if hasattr(kls, "index_definitions"):
                for index in kls.index_definitions:
                    if index not in cls.index_definitions:
                        cls.index_definitions.append(index)

    @classmethod
    def update_sql_emitters(cls) -> None:
        """
        Updates the SQL emitters of the class by extending the current class's
        SQL emitters with those of its parent classes.

        This method iterates through the method resolution order (MRO) of the
        class and checks if each class in the hierarchy has a 'sql_emitters'
        attribute. If it does, the SQL emitters of the current class are extended
        with the SQL emitters of that class.

        Returns:
            None
        """
        sql_emitters = []
        for kls in cls.mro():
            if hasattr(kls, "sql_emitters"):
                for sql_emitter in kls.sql_emitters:
                    if sql_emitter not in sql_emitters:
                        sql_emitters.append(sql_emitter)
        cls.sql_emitters = sql_emitters

    @classmethod
    def create_routers(cls) -> None:
        for router_def in cls.router_defs.values():
            cls.routers.append(
                Router(
                    table=cls.table,
                    model=cls,
                    obj_name=cls.table_name,
                    method=router_def.method,
                    endpoint=router_def.endpoint,
                    path_objs="",
                    path_module=cls.table_name,
                    path_suffix=router_def.path_suffix,
                    multiple=router_def.multiple,
                    include_in_schema=router_def.include_in_schema,
                    tags=[cls.__class__.__name__],
                    summary=router_def.summary,
                    description=router_def.description,
                )
            )

    @classmethod
    def emit_sql(cls) -> str:
        sql = cls.vertex.emit_sql() if cls.vertex else ""
        sql += "\n".join(
            [
                sql_emitter(
                    table_name=cls.table_name, schema_name=cls.schema_name
                ).emit_sql()
                for sql_emitter in cls.sql_emitters
            ]
        )
        return sql

    def generate_insert_sql_robot(self) -> tuple[str, tuple]:
        """
        Generates an SQL INSERT statement for the model's fields using parameterized queries.

        Returns:
            tuple: A tuple containing the SQL INSERT statement and a tuple of values.
        """
        columns = ", ".join(self.field_definitions.keys())
        placeholders = ", ".join(f"%s" for _ in self.field_definitions.keys())
        values = tuple(
            getattr(self, col)
            if not isinstance(getattr(self, col), Enum)
            else getattr(self, col).name
            for col in self.field_definitions.keys()
            if getattr(self, col) is not None
        )
        sql = f"INSERT INTO {self.schema_name}.{self.table_name} ({columns}) VALUES ({placeholders});"
        return sql, values

    def generate_insert_sql(self) -> str:
        """
        Generates an SQL INSERT statement for the model's fields.

        Returns:
            str: The SQL INSERT statement.
        """
        columns = ", ".join(self.field_definitions.keys())
        # values = ", ".join(
        #    f"{getattr(self, col)}" for col in self.field_definitions.keys()
        # )
        _columns = []
        _values = []
        for key, val in self.model_dump().items():
            if not val:
                continue
            _columns.append(key)
            if isinstance(val, Enum):
                _values.append(f"'{val.name}'")
            elif isinstance(val, str):
                _values.append(f"'{val}'")
            else:
                _values.append(f"{val}")
        columns = ", ".join(_columns)
        values = ", ".join(_values)
        return f"INSERT INTO {self.schema_name}.{self.table_name} ({columns}) VALUES ({values});"
