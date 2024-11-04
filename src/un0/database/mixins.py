# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

from typing import Optional, ClassVar

from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import BOOLEAN, TEXT

from pydantic.dataclasses import dataclass

from un0.database.sql_emitters import (
    SQLEmitter,
    SetDefaultActiveSQL,
    InsertTableTypeSQL,
)
from un0.database.fields import FieldDefinition, IX, CK, UQ
from un0.database.models import FieldMixin


class NameMixin(FieldMixin):
    """
    NameMixin is a mixin class that provides a 'name' field definition for models.

    Attributes:
        field_definitions (dict): A dictionary defining the 'name' field with its data
            type, nullability, and documentation.
        name (str): The name of the record.
    """

    field_definitions = {
        "name": FieldDefinition(
            data_type=TEXT,
            nullable=False,
            doc="Name of the record",
        ),
    }

    name: Optional[str] = None


class DescriptionMixin(FieldMixin):
    """
    DescriptionMixin is a mixin class that provides a description field for a model.

    Attributes:
        description (Optional[str]): A string field that holds the description of the record.
            It is optional and can be null.

    Field Definitions:
        field_definitions (dict): A dictionary containing the definition of the description field,
            including its data type, nullability, and documentation.
    """

    field_definitions = {
        "description": FieldDefinition(
            data_type=TEXT,
            doc="Description of the record",
        ),
    }

    description: Optional[str] = None


class NameDescriptionMixin(NameMixin, DescriptionMixin):
    """
    A mixin class that combines the functionality of NameMixin and DescriptionMixin.

    This mixin can be used to add both name and description fields to a model.

    Inheritance:
        NameMixin: A mixin that provides a name field.
        DescriptionMixin: A mixin that provides a description field.
    """

    pass


class ActiveMixin(FieldMixin):
    """
    Mixin class that adds an 'is_active' field to a model.

    SqlEmitter:
        The ActiveFieldSQLEmitter alters the table to add the default of True to the 'is_active'
        field.

    Attributes:
        sql_emitters (list): List of SQL emitters for the mixin.
        field_definitions (dict): Dictionary defining the 'is_active' field.
        is_active (bool): Indicates if the record is active. Defaults to True.
    """

    """ """

    sql_emitters = [SetDefaultActiveSQL]
    field_definitions = {
        "is_active": FieldDefinition(
            data_type=BOOLEAN,
            doc="Indicates if the record is active",
        ),
    }

    is_active: bool = True


class ImportMixin(FieldMixin):
    """
    ImportMixin is a mixin class that provides fields and field definitions for importing
    records from an external system.

    Attributes:
        field_definitions (dict): A dictionary defining the fields for import_id and import_key.
        import_id (Optional[int]): Primary Key of the original system of the record.
        import_key (Optional[str]): Unique identifier of the original system of the record.
    """

    field_definitions = {
        "import_id": FieldDefinition(
            data_type=Integer,
            doc="Primary Key of the original system of the record",
        ),
        "import_key": FieldDefinition(
            data_type=TEXT,
            doc="Unique identifier of the original system of the record",
        ),
    }

    import_id: Optional[int] = None
    import_key: Optional[str] = None


class TableTypeMixin(FieldMixin):
    """ """

    sql_emitters = [InsertTableTypeSQL]
