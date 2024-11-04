# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations
from functools import lru_cache
from typing import Any
from pydantic import BaseModel

# from database import AutoFilterDB  # type: ignore
from un0.database.base.enumerations import (  # type: ignore
    Include,
    Match,
    Lookup,
    FilterValue,
    related_lookups,
    numeric_lookups,
    string_lookups,
)
from un0.config import Settings  # type: ignore


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()


class AutoFilterField(BaseModel):
    id: str | None = None
    source_table: str
    field_name: str
    label: str | None = None
    destination_table: str | None = None
    value_type: FilterValue | None = None
    includes: list[Include] | None = None
    matches: list[Match] | None = None
    lookups: list[Lookup] | None = None
    parent_id: int | None = None

    class Config:
        table_name: str = "autofilter__field"
        reverse_related_tables: list[str] = ["autofilter__filter"]


"""
class FilterFieldCreator:
    tables: dict[str, Table]
    db: AutoFilterDB

    def __init__(self, tables: dict[str, Table]) -> None:
        self.tables = tables
        self.db = AutoFilterDB("autofilter__field")
        for table in self.tables.values():
            # HERE FOR DEVELOPMENT TESTING ONLY
            # TODO REMOVE THIS IF STATEMENT ONCE ALL TESTS PASS
            if not table.name in ["groupauth__user"]:
                continue
            for column in table.columns:
                field_model = self.define_autofilterfield_model(column)
                if self.db.exists_(field_model.exists_fields):
                    if settings.DEBUG:
                        print(f"{field_model} already exists")
                    continue
                print(f"Inserting {field_model}")
                self.db.insert_(field_model.insert_fields)

    def define_autofilterfield_model(self, column) -> AutoFilterField:
        column_dict = {}
        try:
            column_dict["source_table"] = column.table.name
            column_dict["field_name"] = column.name
            column_dict["foreign_keys"] = column.foreign_keys
            column_dict["destination_table"] = self.set_destination(column)
            column_dict["label"] = (
                column.name.replace("_id", "").replace("_", " ").title()
            )
            column_dict["value_type"] = FilterValue[column.type.__class__.__name__]
            column_dict["includes"] = Include
            column_dict["matches"] = Match
            column_dict["lookups"] = self.set_lookups(
                str(column.type.__class__.__name__)
            )
        except AttributeError as e:
            raise Exception(
                f"{e} (Could not extract necessary AutoFilterField information for the column: {column.name} in the table: {column.table.name}.)"
            ) from e
        try:
            print(column_dict)
            autofilterfield = AutoFilterField(**column_dict)
        except TypeError as e:
            raise Exception(
                f"{e} (Could not create AutoFilterField object for the column: {column.name} in the table: {column.table.name}.)"
            ) from e
        return autofilterfield

    def set_destination(self, column):
        if not column.foreign_keys:
            return column.table.name
        for foreign_key in column.foreign_keys:
            return foreign_key.column.table.name

    def set_lookups(self, value_type: str):
        if value_type in [
            FilterValue.TEXT,
            FilterValue.ENUM,
            FilterValue.JSON,
            FilterValue.TEXT,
        ]:
            return string_lookups
        if value_type in [
            FilterValue.DECIMAL,
            FilterValue.BIGINT,
            FilterValue.DATE,
            FilterValue.TIME,
            FilterValue.TIMESTAMP,
        ]:
            return numeric_lookups
        return related_lookups
"""
