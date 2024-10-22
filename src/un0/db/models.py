# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Any, Type, ClassVar

from pydantic import (
    BaseModel,
    ConfigDict,
    create_model,
    computed_field,
    model_validator,
)
from pydantic_core import PydanticUndefined
from pydantic.fields import Field

from sqlalchemy import Table, Column, inspect

from fastapi import APIRouter, Request, Depends, FastAPI


from un0.errors import (
    Un0BaseModelRegistryError,
    Un0BaseModelTableError,
    Un0BaseModelConfigError,
    Un0BaseModelFieldListError,
    Un0BaseModelRelationConfigError,
)
from un0.db.base import engine, Base

meta_data = Base.metadata

_Unset = PydanticUndefined


class Un0RouterDef(BaseModel):
    """
    Un0RouterDef holds the configuration attributes for an Un0Router.

    Attributes:
        path (str): The path for the router.
        tags (list[str]): A list of tags for the router.
        dependencies (list[Depends]): A list of dependencies for the router.
    """

    model: Type["Un0Model"]
    path: str = "/"
    tags: list[str] = []
    dependencies: list[Depends] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Un0ModelDef(BaseModel):
    """
    UnoModelDef holds the configureation attributes for an Un0Model.

    Attributes:
        includes (list[str]): A list of strings representing the fields to include.
        excludes (list[str]): A list of strings representing the fields to exclude.
        router_path (str | None): An optional string representing the router path.
        model_config (ConfigDict): Configuration class freezing the model fields.
    """

    table: Type[Base]
    base: Type["Un0Model"]
    field_includes: list[str] = []
    field_excludes: list[str] = []
    # router_def: Un0RouterDef = Un0RouterDef()

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="before")
    def validate_model(cls, values):
        """
        Validates the model fields based on the provided values.

        Args:
            cls: The class of the model being validated.
            values (dict): A dictionary containing the following keys:
                - table: The table to inspect.
                - field_includes: A list of fields to include.
                - field_excludes: A list of fields to exclude.

        Raises:
            Un0BaseModelFieldListError: If a field in field_includes or field_excludes does not exist in the table.
            Un0BaseModelFieldListError: If both field_includes and field_excludes are provided.
            Un0BaseModelFieldListError: If there are duplicate fields in field_includes or field_excludes.

        Returns:
            dict: The validated values.
        """
        inspector = inspect(values.get("table"))
        for field in values.get("field_includes", []):
            if field not in inspector.columns:
                raise Un0BaseModelFieldListError(
                    "Field in field_excludes does not exist in the table.",
                    "FIELD_NOT_FOUND_IN_TABLE",
                )
        for field in values.get("field_excludes", []):
            if field not in inspector.columns:
                raise Un0BaseModelFieldListError(
                    "Field in field_includes does not exist in the table.",
                    "FIELD_NOT_FOUND_IN_TABLE",
                )

        if values.get("field_includes") and values.get("field_excludes"):
            raise Un0BaseModelFieldListError(
                "You cannot include and exclude fields in the same model.",
                "INCLUDE_AND_EXCLUDE_FIELDS",
            )

        uniques = set()
        include_duplicates = []
        for field in values.get("field_includes", []):
            if field in uniques:
                include_duplicates.append(field)
            else:
                uniques.add(field)

        uniques = set()
        exclude_duplicates = []
        for field in values.get("field_excludes", []):
            if field in uniques:
                exclude_duplicates.append(field)
            else:
                uniques.add(field)
        if include_duplicates:
            raise Un0BaseModelFieldListError(
                f"Duplicate fields found in field_includes: {', '.join(include_duplicates)}, for Un0Model {cls.__name__}.",
                "DUPLICATE_FIELDS_IN_LISTS",
            )
        if exclude_duplicates:
            raise Un0BaseModelFieldListError(
                f"Duplicate fields found in field_excludes: {', '.join(exclude_duplicates)}, for Un0Model {cls.__name__}.",
                "DUPLICATE_FIELDS_IN_LISTS",
            )
        return values


class Un0FrozenModelDef(Un0ModelDef):
    """
    Un0FrozenModelConfig holds the configureation attributes for a frozen Un0Model.

    Attributes:
        includes (list[str]): A list of strings representing the fields to include.
        excludes (list[str]): A list of strings representing the fields to exclude.
        router_path (str | None): An optional string representing the router path.
    """

    model_config = ConfigDict(frozen=True)


class Un0Model(BaseModel):
    """
    Un0Model class that inherits from BaseModel.

    Attributes:
        model_config (ConfigDict): Configuration dictionary allowing arbitrary types.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def process_app_logic(self):
        pass


class Un0Router:
    def __init__(
        self,
        path: str,
        schema: Type[Un0Model],
    ):
        self.schema = schema
        self.path = path

    def register_router(self):
        router = APIRouter()
        router.add_api_route(
            self.path,
            self.get,
            methods=["GET"],
            response_model=self.schema,
        )
        return router

    def get(self):
        return {"message": "Hello World"}


class Un0Obj(BaseModel):
    """
    Un0Obj is the base class for defining models that interact with a database table. It provides mechanisms for
    registering models, creating fields based on SQLAlchemy columns, and generating API models.

    Attributes:
        un0_model_registry (ClassVar[dict[str, Type[BaseModel]]]): Registry to store Un0Obj classes by table name.
        un0_class_name_map (ClassVar[dict[str, str]]): Map to store Un0Obj.table_name classes by model name.
        db_table_name (ClassVar[str]): The name of the database table associated with the model.
        db_table (ClassVar[Table]): The SQLAlchemy Table object associated with the model.
        module_name (ClassVar[str]): The name of the module where the model is defined.
        model_config (dict): Configuration for the model, allowing arbitrary types.

    Methods:
        select_schema(self) -> Type[Un0Obj]:
            Creates an API model based on the database table fields.

        __init_subclass__(cls, module_name=Any, db_table_name: str | None = None, **kwargs) -> None:
            Initializes a subclass of Un0Obj, setting up the database table and registering the subclass.

            The registry is shared by all subclasses
            It is a singleton that exists in the base class and is shared by all subclasses
            un0_model_registry is used to store the Un0Obj classes by table name
            un0_class_name_map is used to store the Un0Obj.table_name classes by model name
            So that we can get the Un0Obj class from the table name and the table name from the model name map

        create_model_field(cls, column: Column) -> tuple[Any, Any]:
            Creates a model field based on the given SQLAlchemy column.

        suss_fields(cls) -> dict[str, Any]:
            Determines the fields for an Un0Obj based on the table columns.

        get_model_from_registry_by_table_name(cls, db_table_name: str) -> Type["BaseModel"] | None:
            Retrieves a model from the registry by the table name.

        get_model_from_registry_by_model_name(cls, model_name: str) -> Type["BaseModel"] | None:
            Retrieves a model from the registry by the model name.
    """

    # models: dict[str, Type[Un0Model]] = {} <- computed_field
    # routers: list[Type[Un0Router]] = [] <- computed_field

    un0_model_registry: ClassVar[dict[str, Type[BaseModel]]] = {}
    un0_class_name_map: ClassVar[dict[str, str]] = {}
    db_table_name: ClassVar[str]
    db_table: ClassVar[Table]
    module_name: ClassVar[str]
    app: FastAPI

    schema_defs: dict[str, dict[str, Un0ModelDef]] = {}
    router_defs: dict[str, dict[str, Un0RouterDef]] = {}

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def models(self) -> dict[str, Un0Model]:
        models = {}
        for model_name, model_def in self.schema_defs.items():
            # Create a Pydantic model using the base class from model_def
            models[model_name] = create_model(
                model_name,
                __base__=model_def.base,
                **self.suss_fields(model_def=model_def),
            )
        return models

    @computed_field
    def routers(self) -> list[Type[Un0Router]]:
        routers = []
        return [
            Un0Router(schema=self.models.get("select_schema"), path="users"),
        ]
        for router_name, router_def in self.router_defs.items():
            routers.append(
                Un0Router(
                    schema=router_def.model,
                    path=router_def.path,
                    tags=router_def.tags,
                    dependencies=router_def.dependencies,
                )
            )
        return routers

    def __init_subclass__(
        cls: Type["Un0Obj"],
        module_name: str,
        db_table_name: str | None = None,
        **kwargs: dict[str, Any],
    ) -> None:
        """
        Initializes a subclass of Un0Obj.

        This method is called when a class is subclassed from Un0Obj. It sets up the database table
        and registers the subclass in the appropriate registries.

        Args:
            cls: The subclass being initialized.
            module_name (Any): The name of the module where the subclass is defined.
            db_table_name (str | None): The name of the database table associated with the subclass.
            **kwargs: Additional keyword arguments.

        Raises:
            Un0BaseModelTableError: If the specified table does not exist in the SQLAlchemy meta_data.
            Un0BaseModelRegistryError: If a class with the specified table name or model name already exists in the registry.
        """

        # This prevents the base class (Un0Obj) from being created and added to the registry
        if db_table_name is not None:
            cls.db_table_name = db_table_name
            cls.module_name = module_name

            # Ensure the table exists in meta_data.tables
            if db_table_name in meta_data.tables:
                cls.db_table = meta_data.tables.get(db_table_name)  # type: ignore # the table is in meta_data.tables
            else:
                raise Un0BaseModelTableError(
                    f"Table {db_table_name} does not exist in the sqlalchemy meta_data.",
                    "TABLE_NOT_FOUND_IN_TABLE_COLLECTION",
                )

            # This is here as we only want to create and add the class to the registry once
            # The BaseClass registry is shared by all subclasses
            # It's like a singleton, it exists in the base class and is shared by all subclasses
            if db_table_name not in cls.un0_model_registry:
                # Add the subclass to the table_name_registry
                cls.un0_model_registry.update({db_table_name: cls})
                # Add the subclass to the model_name_registry if it is not there (shouldn't be there, but just in case)
                if cls.__name__ not in cls.un0_class_name_map:
                    cls.un0_class_name_map.update({cls.__name__: cls.db_table_name})
                else:
                    raise Un0BaseModelRegistryError(
                        f"A class with the table name {db_table_name} already exists.",
                        "MODEL_NAME_EXISTS_IN_REGISTRY",
                    )
            else:
                raise Un0BaseModelRegistryError(
                    f"A class with the table name {db_table_name} already exists.",
                    "TABLE_NAME_EXISTS_IN_REGISTRY",
                )

    @classmethod
    def create_model_field(cls, column: Column) -> tuple[Type, Field]:
        """
        Create a model field based on the given SQLAlchemy column.

        Args:
            column (Column): The SQLAlchemy column to create the model field from.

        Returns:
            tuple[Type, Field]: A tuple containing the field type and the field instance.
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
    def suss_fields(cls, model_def: Un0ModelDef) -> dict[str, Any]:
        """
        Suss out the fields for an Un0Obj based on the table columns.

        Args:
            model_def (Un0ModelDef): The model definition containing field includes and excludes.

        Returns:
            dict[str, Any]: A dictionary of fields for the Un0Model.
        """
        return {
            column.name: cls.create_model_field(column)
            for column in cls.db_table.columns
            if column.name not in model_def.field_excludes
            and (
                not model_def.field_includes or column.name in model_def.field_includes
            )
        }

    @classmethod
    def get_model_from_registry_by_table_name(
        cls,
        db_table_name: str,
    ) -> Type["BaseModel"] | None:
        """
        Retrieve a model class from the registry by its database table name.

        Args:
            db_table_name (str): The name of the database table associated with the model.

        Returns:
            Type["BaseModel"] | None: The model class associated with the given table name,
            or None if the table name is not found in the registry.

        Raises:
            Un0BaseModelRegistryError: If no model is found for the given table name.
        """
        try:
            return cls.un0_model_registry.get(db_table_name)
        except KeyError:
            raise Un0BaseModelRegistryError(
                f"No Un0Obj found for {db_table_name}.", "MODEL_NOT_FOUND"
            )

    @classmethod
    def get_model_from_registry_by_model_name(
        cls,
        model_name: str,
    ) -> Type["BaseModel"] | None:
        """
        Retrieve a model class from the registry using the model name.

        Args:
            model_name (str): The name of the model to retrieve.

        Returns:
            Type["BaseModel"] | None: The model class if found, otherwise None.

        Raises:
            Un0BaseModelRegistryError: If no table is found for the given model name.
        """
        try:
            db_table_name = cls.un0_class_name_map.get(model_name)
            return cls.get_model_from_registry_by_table_name(db_table_name)  # type: ignore
        except KeyError:
            raise Un0BaseModelRegistryError(
                f"No Table found for {cls.db_table_name}.",
                "MODEL_NOT_FOUND_BY_TABLE_NAME",
            )
