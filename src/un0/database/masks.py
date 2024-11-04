# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from typing import Type

from pydantic import BaseModel, model_validator, field_validator, computed_field
from pydantic.dataclasses import dataclass

from un0.database.sql_emitters import SQLEmitter
from un0.database.enums import MaskType, SQLOperation
from un0.config import settings


@dataclass
class ViewEmitter(SQLEmitter):
    def emit_sql(self, mask_name: str, field_list: list[str]) -> str:
        return textwrap.dedent(
            f"""
            SET ROLE {settings.DB_USER}_admin;
            CREATE OR REPLACE VIEW {self.schema_name}.{self.table_name}_{mask_name} AS 
            SELECT {field_list}
            FROM {self.schema_name}.{self.table_name};
            """
        )


class MaskDef(BaseModel):
    name: str | None = None
    mask_type: MaskType = MaskType.NATIVE
    operation: list[SQLOperation] = []
    include_fields: set[str] = set()
    exclude_fields: set[str] = set()
    include_relations: set[str] = set()
    sql_emitters: list[Type[SQLEmitter]] = []

    @model_validator(mode="after")
    def validate_model(cls, value):
        if value.include_fields and value.exclude_fields:
            raise ValueError("Both include_fields and exclude_fields cannot be set.")
        if value.include_relations:
            pass
        if value.operation == SQLOperation.SELECT:
            cls.create_view()
        return value

    @field_validator("name", mode="before")
    def name(cls, data) -> list[str]:
        if not data:
            return cls.operation.value
        return data


class Mask(BaseModel):
    """
    Enum class for model masks.
    """

    # field_list: list[str] = [] <- computed_field

    table_name: str
    name: str
    schema_name: str = settings.DB_NAME

    @classmethod
    def create_view(cls) -> None:
        cls.sql_emitters.append(ViewEmitter().emit_sql())

    @classmethod
    def emit_sql(cls) -> str:
        if cls.mask_type != MaskType.SELECT:
            return ""
        return "\n".join(
            [f"{sql_emitter().emit_sql()}" for sql_emitter in cls.sql_emitters]
        )
