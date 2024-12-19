# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Any, Type, ClassVar, List, Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    create_model,
    computed_field,
    model_validator,
    field_validator,
)
from pydantic_core import PydanticUndefined
from pydantic.fields import Field

from sqlalchemy import (
    Table,
    Column,
    inspect,
    func,
    select,
    update,
    delete,
    insert,
)
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Request, Depends, FastAPI, Header, HTTPException

from un0.errors import (
    ModelRegistryError,
    ModelTableError,
    ModelFieldListError,
    ModelConfigError,
    ModelRelationConfigError,
)
# from un0.database.base import Base, get_db


metadata = Base.metadata

_Unset = PydanticUndefined


class Un0RouterDef(BaseModel):
    un0_model_name: str | None = None
    path_suffix: str | None = None
    path_objs: str = ""
    method: str = "GET"
    endpoint: str = "get"
    multiple: bool = False
    include_in_schema: bool = True
    summary: str = ""
    description: str = ""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class Un0Router(BaseModel):
    # path: str <- computed_field

    table: Type[Base]
    app: FastAPI
    model: Any
    obj_name: str
    path_objs: str
    path_module: str
    path_suffix: str | None = None
    method: str = "GET"
    endpoint: str = "get"
    multiple: bool = False
    include_in_schema: bool = True
    summary: str = ""
    description: str = ""
    tags: list[str] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def path(self) -> str:
        suffix = f"/{self.path_suffix}" if self.path_suffix else ""
        return f"/api/{self.path_module}/{self.path_objs}{suffix}"

    def add_to_app(self):
        router = APIRouter()
        router.add_api_route(
            self.path,
            endpoint=getattr(self, self.endpoint),
            methods=[self.method],
            response_model=self.model if not self.multiple else List[self.model],
            include_in_schema=self.include_in_schema,
            tags=self.tags,
            summary=self.summary,
            description=self.description,
        )
        self.app.include_router(router)
        return router

    async def get_by_id(
        self,
        id: str,
        authorization: Annotated[str, Header()],
        db: AsyncSession = Depends(get_db),
    ):
        await db.execute(func.un0.authorize_user(authorization))
        result = await db.execute(select(self.table).filter_by(id=id))
        obj = result.scalar()
        if obj is None:
            raise HTTPException(status_code=404, detail="Object not found")
        return obj

    async def get(
        self,
        authorization: Annotated[str, Header()],
        db: AsyncSession = Depends(get_db),
    ):
        await db.execute(func.un0.authorize_user(authorization))
        result = await db.execute(select(self.table))
        return result.scalars()

    async def post(
        self,
        request: Request,
        authorization: Annotated[str, Header()],
        db: AsyncSession = Depends(get_db),
    ):
        await db.execute(func.un0.authorize_user(authorization))
        data = await request.json()
        await db.execute(self.table.insert().values(data))
        return {"message": "post"}

    def put(self):
        return {"message": "put"}

    def delete(self):
        return {"message": "delete"}


class Un0ModelDef(BaseModel):
    table: Type[Base]
    field_includes: list[str] = []
    field_excludes: list[str] = []
    use_defaults: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="before")
    def validate_model(cls, values):
        # Validate the model fields provided in field_includes and field_excludes
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

        # Create the default list of fields to include based on the use_defaults value
        defaults = values.get("use_defaults")
        if defaults:
            field_includes = [
                field.name
                for field in inspector.columns
                if (
                    field.info.get("editable", True)
                    and (defaults == "Insert" and not field.server_default)
                    or field.info.get("editable", True)
                    and (defaults == "Update" and not field.server_onupdate)
                    or field.info.get("editable", True)
                    and (defaults == "Unique" and field.unique)
                )
            ]
            values["field_includes"] = field_includes
        return values


class Un0FrozenSchemaDef(Un0ModelDef):
    model_config = ConfigDict(frozen=True)


class Un0Model(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def generate_insert_sql(self) -> str:
        """
        Generates an SQL INSERT statement for the model's fields.
        
        Returns:
            str: The SQL INSERT statement.
        """
        table_name = self.__class__.table_name
        columns = ', '.join(self.__annotations__.keys())
        values = ', '.join(f"'{getattr(self, col)}'" for col in self.__annotations__.keys())
        return f"INSERT INTO {table_name} ({columns}) VALUES ({values});"


class Un0Obj(BaseModel):
    # models: dict[str, Type[Un0Model]] = {} <- computed_field
    # routers: list[Type[Un0Router]] = [] <- computed_field

    un0_model_registry: ClassVar[dict[str, Type[BaseModel]]] = {}
    un0_class_name_map: ClassVar[dict[str, str]] = {}
    module_name: ClassVar[str]
    table_name: ClassVar[str]
    table: ClassVar[Table]
    un0_model_base: ClassVar[Type[Un0Model]]

    app: FastAPI
    un0_model_defs: dict[str, dict[str, Un0ModelDef]] = {}
    default_un0_model_names: list[str] = ["Insert", "Update", "Select", "List"]
    un0_router_defs: dict[str, dict[str, Un0RouterDef]] = {}
    default_un0_router_defs: dict[str, Un0RouterDef] = {
        "Insert": Un0RouterDef(
            method="POST",
            endpoint="post",
        ),
        "List": Un0RouterDef(
            method="GET",
            endpoint="get",
            multiple=True,
        ),
        "Update": Un0RouterDef(
            path_suffix="{id}",
            method="PUT",
            endpoint="put",
        ),
        "Select": Un0RouterDef(
            path_suffix="{id}",
            method="GET",
            endpoint="get_by_id",
        ),
        "Delete": Un0RouterDef(
            path_suffix="{id}",
            method="DELETE",
            endpoint="delete",
        ),
    }
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def models(self) -> dict[str, Un0Model]:
        models = {}
        # Creates the models defined in the default_un0_model_defs
        # May be overriden by the un0_model_defs or by declaring
        # default_un0_model_defs in the subclass
        for model_prefix in self.default_un0_model_names:
            model_name = f"{model_prefix}{self.table_name.split(".")[1].capitalize()}"
            models.update(
                {
                    model_name: create_model(
                        model_name,
                        __base__=self.model_base,
                        __module__=self.module_name,
                        **self.suss_fields(
                            model_def=Un0ModelDef(
                                table=self.table,
                                use_defaults=model_prefix,
                            )
                        ),
                    )
                }
            )
        # Creates the models defined in the un0_model_defs
        # May override the defaults to include or exclude additional fields
        for model_name, model_def in self.un0_model_defs.items():
            models.update(
                {
                    model_name: create_model(
                        model_name,
                        __base__=self.model_base,
                        __module__=self.module_name,
                        **self.suss_fields(model_def=model_def),
                    )
                }
            )
        return models

    @computed_field
    def routers(self) -> list[Type[Un0Router]]:
        routers = []
        for name, router_def in self.default_un0_router_defs.items():
            model_name = f"{name}{self.obj_name}"
            if self.models.get(model_name):
                # Ensure the model for the route exists
                routers.append(
                    Un0Router(
                        table=self.table,
                        model=self.models.get(model_name),
                        obj_name=self.obj_name,
                        app=self.app,
                        method=router_def.method,
                        endpoint=router_def.endpoint,
                        path_objs=self.path_objs,
                        path_module=self.module_name,
                        path_suffix=router_def.path_suffix,
                        multiple=router_def.multiple,
                        include_in_schema=router_def.include_in_schema,
                        tags=[self.module_name],
                        summary=router_def.summary,
                        description=router_def.description,
                    )
                )
        for router_def in self.un0_router_defs.values():
            if self.models.get(router_def.un0_model_name):
                # Ensure the model for the route exists
                routers.append(
                    Un0Router(
                        table=self.table,
                        model=self.models.get(router_def.un0_model_name),
                        app=self.app,
                        method=router_def.method,
                        endpoint=router_def.endpoint,
                        path_objs=self.path_objs,
                        path_module=self.module_name,
                        path_suffix=router_def.path_suffix,
                        multiple=router_def.multiple,
                        include_in_schema=router_def.include_in_schema,
                        tags=[self.module_name],
                        summary=router_def.summary,
                        description=router_def.description,
                    )
                )
        return routers

    def __init_subclass__(
        cls: Type["Un0Obj"],
        table_name: str,
        table: Table,
        module_name: str,
        obj_name: str,
        path_objs: str,
        model_base: Type[Un0Model],
        **kwargs: dict[str, Any],
    ) -> None:
        # This prevents the base class (Un0Obj) from being created and added to the registry
        if table_name is not None:
            cls.table_name = table_name
            cls.table = table
            cls.module_name = module_name
            cls.obj_name = obj_name
            cls.path_objs = path_objs
            cls.model_base = model_base

            # Ensure the table exists in metadata.tables
            if table_name in metadata.tables:
                cls.db_table = metadata.tables.get(table_name)
            else:
                raise Un0BaseModelTableError(
                    f"Table {table_name} does not exist in the sqlalchemy metadata.",
                    "TABLE_NOT_FOUND_IN_TABLE_COLLECTION",
                )

            # This is here as we only want to create and add the class to the registry once
            # The BaseClass registry is shared by all subclasses
            # It's like a singleton, it exists in the base class and is shared by all subclasses
            if table_name not in cls.un0_model_registry:
                # Add the subclass to the table_name_registry
                cls.un0_model_registry.update({table_name: cls})
                # Add the subclass to the model_name_registry if it is not there (shouldn't be there, but just in case)
                if cls.__name__ not in cls.un0_class_name_map:
                    cls.un0_class_name_map.update({cls.__name__: cls.table_name})
                else:
                    raise Un0BaseModelRegistryError(
                        f"A class with the table name {table_name} already exists.",
                        "MODEL_NAME_EXISTS_IN_REGISTRY",
                    )
            else:
                raise Un0BaseModelRegistryError(
                    f"A class with the table name {table_name} already exists.",
                    "TABLE_NAME_EXISTS_IN_REGISTRY",
                )

    @classmethod
    def create_model_field(cls, column: Column) -> tuple[Type, Field]:
        field_type = column.type.python_type
        nullable = column.nullable
        default = None if column.server_default or nullable else column.default or ...
        default_factory = column.default if callable(column.default) else _Unset

        field = Field(
            default=default,
            default_factory=default_factory,
            title=column.name.title(),
            description=column.doc or column.name,
        )
        return (field_type | None, field) if nullable else (field_type, field)

    @classmethod
    def suss_fields(cls, model_def: Un0ModelDef) -> dict[str, Any]:
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
        table_name: str,
    ) -> Type["BaseModel"] | None:
        try:
            return cls.un0_model_registry.get(table_name)
        except KeyError:
            raise Un0BaseModelRegistryError(
                f"No Un0Obj found for {table_name}.", "MODEL_NOT_FOUND"
            )

    @classmethod
    def get_model_from_registry_by_model_name(
        cls,
        model_name: str,
    ) -> Type["BaseModel"] | None:
        try:
            table_name = cls.un0_class_name_map.get(model_name)
            return cls.get_model_from_registry_by_table_name(table_name)  # type: ignore
        except KeyError:
            raise Un0BaseModelRegistryError(
                f"No Table found for {cls.table_name}.",
                "MODEL_NOT_FOUND_BY_TABLE_NAME",
            )
