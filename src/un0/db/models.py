# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Any, Type, ClassVar

from pydantic import BaseModel, create_model, computed_field
from pydantic_core import PydanticUndefined
from pydantic.fields import Field

from sqlalchemy import Table, Column

from fastapi import APIRouter, Request, Depends


from un0.errors import (
    Un0ModelRegistryError,
    Un0ModelTableError,
    Un0ModelConfigError,
    Un0ModelFieldListError,
    Un0ModelRelationConfigError,
)
from un0.db.base import engine, Base

meta_data = Base.metadata

_Unset = PydanticUndefined


class Un0Model(BaseModel):
    table: Table

    model_config = {"arbitrary_types_allowed": True}


class Un0Router(APIRouter):
    pass


class Un0Base(BaseModel):
    # The registry is shared by all subclasses
    # It is like a singleton, but they exist in the base class and are shared by all subclasses
    # un0_registry is used to store the Un0Model classes by table name
    # un0_class_name_map is used to store the Un0Model.table_name classes by model name
    # So that we can get the Un0Model class from the table name and the table name from the model name map

    # api_model: Type[Un0Model] <- computed_field
    # routers: list[Un0Router] <- computed_field
    # html_model: Type[Un0Model] <- computed_field

    # additional_models: list[Type[Un0Model]]

    un0_registry: ClassVar[dict[str, Type[BaseModel]]] = {}
    un0_class_name_map: ClassVar[dict[str, str]] = {}

    fields: ClassVar[dict[str, Any]] = {}
    db_table_name: ClassVar[str]
    db_table: ClassVar[Table]
    module_name: ClassVar[str]

    model_config = {"arbitrary_types_allowed": True}

    @computed_field
    def api_model(self) -> Type[Un0Model]:
        model_name = f"{self.db_table.name.title()}APIModel"
        return create_model(model_name, **self.suss_fields())

    def __init_subclass__(
        cls, module_name=Any, db_table_name: str | None = None, **kwargs
    ) -> None:
        """
        Initializes a subclass of Un0Model.

        This method is called when a class is subclassed from Un0Model. It sets up the database table
        and registers the subclass in the appropriate registries.

        Args:
            cls: The subclass being initialized.
            module_name (Any): The name of the module where the subclass is defined.
            db_table_name (str | None): The name of the database table associated with the subclass.
            **kwargs: Additional keyword arguments.

        Raises:
            Un0ModelTableError: If the specified table does not exist in the SQLAlchemy meta_data.
            Un0ModelRegistryError: If a class with the specified table name or model name already exists in the registry.
        """

        # This prevents the base class (Un0Model) from being created and added to the registry
        if db_table_name is not None:
            cls.db_table_name = db_table_name
            cls.module_name = module_name

            # Ensure the table exists in meta_data.tables
            if db_table_name in meta_data.tables:
                cls.db_table = meta_data.tables.get(db_table_name)  # type: ignore # the table is in meta_data.tables
            else:
                raise Un0ModelTableError(
                    f"Table {db_table_name} does not exist in the sqlalchemy meta_data.",
                    "TABLE_NOT_FOUND_IN_TABLE_COLLECTION",
                )

            # This is here as we only want to create and add the class to the registry once
            # The BaseClass registry is shared by all subclasses
            # It's like a singleton, it exists in the base class and is shared by all subclasses
            if db_table_name not in cls.un0_registry:
                # Add the subclass to the table_name_registry
                cls.un0_registry.update({db_table_name: cls})
                # Add the subclass to the model_name_registry if it is not there (shouldn't be there, but just in case)
                if cls.__name__ not in cls.un0_class_name_map:
                    cls.un0_class_name_map.update({cls.__name__: cls.db_table_name})
                else:
                    raise Un0ModelRegistryError(
                        f"A class with the table name {db_table_name} already exists.",
                        "MODEL_NAME_EXISTS_IN_REGISTRY",
                    )
            else:
                raise Un0ModelRegistryError(
                    f"A class with the table name {db_table_name} already exists.",
                    "TABLE_NAME_EXISTS_IN_REGISTRY",
                )

    @classmethod
    def create_model_field(cls, column: Column) -> tuple[Any, Any]:
        """
        Create a model field based on the given SQLAlchemy column.

        Args:
            column (Column): The SQLAlchemy column to create the model field from.

        Returns:
            tuple[Any, Any]: A tuple containing the field type and the field instance.
        """
        default = _Unset
        default_factory = _Unset
        title = _Unset
        description = _Unset or column.help_text or column.name
        title = column.name.title()
        field_type = column.type.python_type
        nullable = column.nullable
        if column.server_default:
            default = None
        elif column.default:
            if callable(column.default):
                default_factory = column.default
            else:
                default = column.default
        elif nullable:
            default = None
        else:
            default = ...
        field = Field(
            default=default,
            default_factory=default_factory,
            title=title,
            description=description,
        )
        if nullable:
            return (field_type | None, field)
        return (field_type, field)

    @classmethod
    def suss_fields(cls) -> dict[str, Any]:
        """
        Suss out the fields for an Un0Model based on the table columns.

        Args:
            cls (type): The class object.

        Returns:
            A dictionary of fields for the Un0Model.
        """
        fields = {}
        for column in cls.db_table.columns:
            column_name = column.name
            field = cls.create_model_field(column)
            if column_name not in fields:
                fields[column_name] = field
        return fields

    @classmethod
    def get_model_from_registry_by_table_name(
        cls, db_table_name: str
    ) -> Type["BaseModel"] | None:
        try:
            return cls.un0_registry.get(db_table_name)
        except KeyError:
            raise Un0ModelRegistryError(
                f"No Un0Model found for {db_table_name}.", "MODEL_NOT_FOUND"
            )

    @classmethod
    def get_model_from_registry_by_model_name(
        cls,
        model_name: str,
    ) -> Type["BaseModel"] | None:
        try:
            db_table_name = cls.un0_class_name_map.get(model_name)
            return cls.get_model_from_registry_by_table_name(db_table_name)  # type: ignore
        except KeyError:
            raise Un0ModelRegistryError(
                f"No Table found for {cls.db_table_name}.",
                "MODEL_NOT_FOUND_BY_TABLE_NAME",
            )
