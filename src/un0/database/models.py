# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT


from typing import Type, ClassVar
from pydantic import BaseModel
from pydantic.dataclasses import dataclass, Field

from sqlalchemy import Table

from un0.errors import ModelRegistryError
from un0.utilities import convert_snake_to_title
from un0.database.sql_emitters import SQLEmitter, AlterGrantSQL, InsertTableTypeSQL
from un0.database.fields import IX, CK, UQ, FieldDefinition
from un0.database.masks import Mask, MaskDef
from un0.database.enums import Cardinality, MaskType, SQLOperation
from un0.database.routers import RouterDef, Router
from un0.database.base import metadata
from un0.config import settings


@dataclass
class RelatedModel:
    source: Type["Model"]
    cardinality: Cardinality = Cardinality.MANY_TO_ONE
    models: list[Type["Model"]] = Field(default_factory=list)


class Model(BaseModel):
    table: ClassVar[Table]

    registry: ClassVar[dict[str, "Model"]] = {}
    class_name_map: ClassVar[dict[str, str]] = {}

    schema_name: ClassVar[str]
    table_name: ClassVar[str]
    table_name_plural: ClassVar[str]
    verbose_name: ClassVar[str]
    verbose_name_plural: ClassVar[str]
    table_comment: ClassVar[str] = ""
    field_definitions: ClassVar[dict[str, "FieldDefinition"]] = {}
    indices: ClassVar[list[IX]] = []
    constraints: ClassVar[list[CK | UQ]] = []
    sql_emitters: ClassVar[list[str, Type[SQLEmitter]]] = []
    related_models: ClassVar[dict[str, Type["RelatedModel"]]] = {}
    include_in_graph: ClassVar[bool] = True

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

        This method is automatically called when a new subclass is created. It sets up
        various class attributes and ensures the subclass is properly registered.

        Args:
            cls: The subclass being initialized.
            schema_name (str | None): The database schema_name name. Defaults to the value of settings.DB_NAME.
            table_name (str | None): The name of the table. Defaults to None.
            table_name_plural (str | None): The plural name of the table. Defaults to None.
            verbose_name (str | None): A human-readable name for the table. Defaults to None.
            verbose_name_plural (str | None): A human-readable plural name for the table. Defaults to None.

        Raises:
            ModelRegistryError: If a class with the same table name or model name already exists in the registry.

        Notes:
            - This method prevents the base class from being created and added to the registry.
            - It updates field definitions, constraints, and indices from the parent classes.
            - It sets various class attributes such as table_name, schema_name, table_name_plural, verbose_name, and verbose_name_plural.
            - It ensures the subclass is added to the registry only once.
            - It creates the SQLAlchemy table object and adds columns, constraints, and indices to it.
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

        # Update the field_definitions, constraints, and indices from the parent classes
        cls.update_field_definitions()
        cls.update_constraints()
        cls.update_indices()

        # Create and add columns to the SQLAlchemy table object
        columns = []
        # Add the columns to the table
        for field_name, field_definition in cls.field_definitions.items():
            columns.append(field_definition.create_column(name=field_name))

        constraints = []
        # Add the constraints to the table
        for constraint in cls.constraints:
            constraints.append(constraint.create_constraint())

        # Create the sqlalchemy table object
        table = Table(
            cls.table_name,
            metadata,
            schema=cls.schema_name,
            comment=cls.table_comment,
            *columns,
            *constraints,
        )
        # Add the indices to the table
        # Indices are added to improve the performance of database operations
        for index in cls.indices:
            table.indexes.add(index.create_index(table))

        # Set the table attribute on the class to the created SQLAlchemy table object
        cls.table = table

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
        for kls in cls.mro():
            if hasattr(kls, "field_definitions"):
                cls.field_definitions.update(kls.field_definitions)

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
            if hasattr(kls, "constraints"):
                for constraint in kls.constraints:
                    if constraint not in cls.constraints:
                        cls.constraints.append(kls.constraints)

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
        for kls in cls.mro():
            if hasattr(kls, "indices"):
                for index in kls.indices:
                    if index not in cls.indices:
                        cls.indices.append(index)

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
        for kls in cls.mro():
            if hasattr(kls, "sql_emitters"):
                for sql_emitter in kls.sql_emitters:
                    if sql_emitter not in cls.sql_emitters:
                        cls.sql_emitters.append(sql_emitter)

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
        cls.update_sql_emitters()
        return "\n".join(
            [
                sql_emitter(
                    table_name=cls.table_name, schema_name=cls.schema_name
                ).emit_sql()
                for sql_emitter in cls.sql_emitters
            ]
        )

    def process_app_logic(self):
        pass
