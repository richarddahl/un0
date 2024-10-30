# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime

from typing import Optional, ClassVar, Any

from sqlalchemy import (
    text,
    func,
    Integer,
)
from sqlalchemy.dialects.postgresql import (
    TIMESTAMP,
    BOOLEAN,
)

from pydantic.dataclasses import dataclass

from un0.db.sql_emitters import (
    SQLEmitter,
    CreatedModifiedSQLEmitter,
    TrashSQLEmitter,
)
from un0.db.models import Model
from un0.db.fields import FieldDefinition, FK, IX, CK, UQ
from un0.db.types import str_26, str_128, str_255


@dataclass
class ModelMixin:
    """
    ModelMixin class provides a base mixin for database models with common attributes and methods.

    Attributes:
        field_definitions (ClassVar[dict[str, FieldDefinition]]): A dictionary mapping field names to their definitions.
        indices (ClassVar[list[IX]]): A list of index definitions.
        constraints (ClassVar[list[CK | UQ]]): A list of constraint definitions.
        sql_emitters (ClassVar[list[SQLEmitter]]): A list of SQL emitters.

    Methods:
        emit_sql() -> str: Emits the SQL representation of the model.
    """

    field_definitions: ClassVar[dict[str, "FieldDefinition"]] = {}
    indices: ClassVar[list[IX]] = []
    constraints: ClassVar[list[CK | UQ]] = []
    sql_emitters: ClassVar[list[SQLEmitter]] = []

    def emit_sql(self) -> str:
        return super().emit_sql()


class RelatedObjectMixin(ModelMixin):
    """
    RelatedObjectMixin is a mixin class that provides a field definition for a related object.

    Attributes:
        field_definitions (dict): A dictionary defining the fields for the model. It includes:
            - id: A FieldDefinition object with the following properties:
                - data_type: The data type of the field.
                - foreign_key: A foreign key constraint with target, name, and ondelete properties.
                - primary_key: Boolean indicating if the field is a primary key.
                - index: Boolean indicating if the field should be indexed.
                - unique: Boolean indicating if the field should be unique.
                - nullable: Boolean indicating if the field can be null.
                - server_default: Default value for the field on the server side.
                - doc: Documentation string for the field.
                - to_fk_edge_name: Name of the edge from the foreign key.
                - from_fk_edge_name: Name of the edge to the foreign key.

    Attributes:
        id (Optional[str]): The ID of the related object.
        related_object (Optional[Model]): The related object instance.
    """

    field_definitions = {
        "id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(
                target="un0.related_object.id",
                name="uq_related_object_id",
                ondelete="CASCADE",
            ),
            primary_key=True,
            index=True,
            unique=True,
            nullable=False,
            server_default=func.un0.insert_related_object("un0", "user"),
            doc="Primary Key",
            to_fk_edge_name="HAS_ID",
            from_fk_edge_name="IS_ID_OF",
        ),
    }

    id: Optional[str] = None
    related_object: Optional[Model] = None


class ActiveMixin(ModelMixin):
    """
    ActiveMixin is a mixin class that adds an 'is_active' boolean field to a model.
    This field indicates whether the record is active or not.

    Attributes:
        field_definitions (dict): A dictionary defining the 'is_active' field with its data type,
            default value, and documentation.
        is_active (bool): A boolean attribute that defaults to True, indicating the record is
            active by default.
    """

    field_definitions = {
        "is_active": FieldDefinition(
            data_type=BOOLEAN,
            server_default=text("true"),
            doc="Indicates if the record is active",
        ),
    }

    is_active: bool = True


class TrashMixin(ModelMixin):
    """
    TrashMixin is a mixin class that adds soft delete functionality to a model.

    Attributes:
        sql_emitters (list): List of SQL emitters to handle SQL operations.
        field_definitions (dict): Definitions of fields related to soft delete functionality.
            - is_deleted (FieldDefinition): Boolean field indicating if the record is deleted.
            - deleted_at (FieldDefinition): Timestamp field indicating when the record was deleted.
            - deleted_by_id (FieldDefinition): String field representing the ID of the user who
                deleted the record.

        is_deleted (bool): Indicates if the record is deleted. Defaults to False.
        deleted_at (Optional[datetime.datetime]): Time at which the record was deleted. Defaults to None.
        deleted_by_id (Optional[str]): ID of the user who deleted the record. Defaults to None.
        deleted_by (Optional[Model]): User model instance representing the user who deleted the record.
            Defaults to None.
    """

    sql_emitters = [TrashSQLEmitter]
    field_definitions = {
        "is_deleted": FieldDefinition(
            data_type=BOOLEAN,
            server_default=text("false"),
            doc="Indicates if the record is deleted",
        ),
        "deleted_at": FieldDefinition(
            data_type=TIMESTAMP(timezone=True),
            doc="Time at which the record was deleted",
        ),
        "deleted_by_id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(
                target="un0.user.id",
                ondelete="CASCADE",
            ),
            index=True,
            doc="User that deleted the record",
            to_fk_edge_name="DELETED_BY",
            from_fk_edge_name="DELETED",
        ),
    }

    is_deleted: bool = False
    deleted_at: Optional[datetime.datetime] = None
    deleted_by_id: Optional[str] = None
    deleted_by: Optional[Model] = None


class CreatedModifiedMixin(ModelMixin):
    """
    Mixin class that adds created and modified timestamp fields, along with ownership information to a model.

    Attributes:
        created_at (Optional[datetime.datetime]): The timestamp when the record was created.
        owned_by_id (Optional[str]): The ID of the user who owns the record.
        owned_by (Optional[Model]): The user who owns the record.
        modified_at (Optional[datetime.datetime]): The timestamp when the record was last modified.
        modified_by_id (Optional[str]): The ID of the user who last modified the record.
        modified_by (Optional[Model]): The user who last modified the record.

    Field Definitions:
        created_at: FieldDefinition for the creation timestamp.
        owned_by_id: FieldDefinition for the ID of the owning user.
        modified_at: FieldDefinition for the modification timestamp.
        modified_by_id: FieldDefinition for the ID of the modifying user.

    SQL Emitters:
        sql_emitters: List of SQL emitters used for handling created and modified timestamps.
    """

    sql_emitters = [CreatedModifiedSQLEmitter]
    field_definitions = {
        "created_at": FieldDefinition(
            data_type=TIMESTAMP(timezone=True),
            server_default=func.current_timestamp(),
            doc="Time the record was created",
            editable=False,
        ),
        "owned_by_id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(target="un0.user.id", ondelete="CASCADE"),
            index=True,
            doc="User that owns the record",
            to_fk_edge_name="OWNED_BY",
            from_fk_edge_name="OWNS",
        ),
        "modified_at": FieldDefinition(
            data_type=TIMESTAMP(timezone=True),
            server_default=func.current_timestamp(),
            server_onupdate=func.current_timestamp(),
            doc="Time the record was modified_at",
            editable=False,
        ),
        "modified_by_id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(target="un0.user.id", ondelete="CASCADE"),
            index=True,
            doc="User that last modified the record",
            to_fk_edge_name="LAST_MODIFIED_BY",
            from_fk_edge_name="LAST_MODIFIED",
        ),
    }

    created_at: Optional[datetime.datetime] = None
    owned_by_id: Optional[str] = None
    owned_by: Optional[Model] = None
    modified_at: Optional[datetime.datetime] = None
    modified_by_id: Optional[str] = None
    modified_by: Optional[Model] = None


class ImportMixin(ModelMixin):
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
            data_type=str_128,
            doc="Unique identifier of the original system of the record",
        ),
    }

    import_id: Optional[int] = None
    import_key: Optional[str] = None


class NameMixin(ModelMixin):
    """
    NameMixin is a mixin class that provides a 'name' field definition for models.

    Attributes:
        field_definitions (dict): A dictionary defining the 'name' field with its data
            type, nullability, and documentation.
        name (str): The name of the record.
    """

    field_definitions = {
        "name": FieldDefinition(
            data_type=str_128,
            nullable=False,
            doc="Name of the record",
        ),
    }

    name: str


class DescriptionMixin(ModelMixin):
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
            data_type=str_255,
            nullable=True,
            doc="Description of the record",
        ),
    }

    description: Optional[str] = None


class TenantMixin(ModelMixin):
    """
    TenantMixin is a mixin class that provides tenant-related fields and functionality to a model.

    Attributes:
        field_definitions (dict): A dictionary defining the tenant_id field with its properties,
            including data type, foreign key constraints, index, nullability, documentation, and
            edge names for relationships.
        tenant_id (str): The ID of the tenant to which the record belongs.
        tenant (Model): The tenant model instance associated with the tenant_id.
    """

    field_definitions = {
        "tenant_id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(
                target="un0.tenant.id",
                ondelete="CASCADE",
            ),
            index=True,
            nullable=True,
            doc="Tenant to which the record belongs",
            to_fk_edge_name="BELONGS_TO",
            from_fk_edge_name="HAS",
        ),
    }

    tenant_id: str
    tenant: Optional[Model] = None
