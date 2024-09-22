# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from sqlalchemy import Table

from un0.db_definition import un0DB  # type: ignore
from enumerations import (  # type: ignore
    Include,
    Match,
    FieldType,
    select_lookups,
    numeric_lookups,
    string_lookups,
)
from un0.fltr.models import Field  # type: ignore
from un0.config import settings  # type: ignore


def create_fields(tables: dict[str, Table]) -> None:
    """
    Creates UnoFields for the given tables in the database.

    Args:
        tables (dict[str, Table]): A dictionary of tables where the keys are table names and the values are Table objects.
        db (UnoDB): The UnoDB object representing the database.

    Returns:
        None
    """
    for table in tables.values():
        # HERE FOR DEVELOPMENT TESTING ONLY
        # TODO REMOVE THIS IF STATEMENT ONCE ALL TESTS PASS
        if table.name not in ["user"]:
            continue
        for column in table.columns:
            field = define_field(column)
            # if mask := field.masks.get("native_mask"):
            # print(mask.model_dump())
            # print("")
            # for d in field.__dict__:
            #    print(d, field.__dict__[d])
            # if db.exists_(field_model.exists_fields()):
            #    if settings.DEBUG:
            #        print(f"Field {field_model} already exists.")
            #    continue
            # print(f"Inserting Field {field_model}.")
            # db.insert_(field_model.insert_fields())


def define_field(column) -> Field:
    """
    Define a Field object based on the given column.

    Args:
        column: The column object representing the database column.

    Returns:
        An instance of the Field class.

    Raises:
        Exception: If required information cannot be extracted from the column.

    """
    column_dict = {}
    try:
        column_dict["table"] = column.table.name
        column_dict["field_name"] = column.name
        column_dict["label"] = column.name.replace("_id", "").replace("_", " ").title()
        column_dict["value_type"] = FieldType[column.type.__class__.__name__]
        column_dict["includes"] = Include
        column_dict["matches"] = Match
        column_dict["lookups"] = set_lookups(str(column.type.__class__.__name__))

    except AttributeError as e:
        raise Exception(
            f"{e} (Could not extract required information for the column: {column.name} in the table: {column.table.name}.)"
        ) from e
    try:
        field = Field(**column_dict)
    except TypeError as e:
        raise Exception(
            f"{e} (Could not create Field object for the column: {column.name} in the table: {column.table.name}.)"
        ) from e
    return field


def set_lookups(value_type: str):
    """
    Returns the appropriate lookup based on the given value type.

    Args:
        value_type (str): The type of value for which the lookup is needed.

    Returns:
        list: The lookup list corresponding to the given value type.
    """
    if value_type in [
        FieldType.VARCHAR,
        FieldType.ENUM,
        FieldType.JSON,
        FieldType.TEXT,
    ]:
        return string_lookups
    if value_type in [
        FieldType.DECIMAL,
        FieldType.BIGINT,
        FieldType.DATE,
        FieldType.TIME,
        FieldType.TIMESTAMP,
    ]:
        return numeric_lookups
    return select_lookups
