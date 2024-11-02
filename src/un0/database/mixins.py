# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime

from typing import Optional, ClassVar

from sqlalchemy import (
    text,
    Integer,
)
from sqlalchemy.dialects.postgresql import (
    TIMESTAMP,
    BOOLEAN,
)

from pydantic.dataclasses import dataclass

from un0.database.sql.sql_emitter import SQLEmitter
from un0.database.sql.model_sql_emitters import (
    CreatedModifiedSQLEmitter,
    SoftDeleteSQLEmitter,
    RelatedObjectSQLEmitter,
)
from un0.database.models import Model
from un0.database.fields import FieldDefinition, FK, IX, CK, UQ
from un0.database.pg_types import str_26, str_128, str_255


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
                - to_edge: Name of the edge from the foreign key.
                - from_edge: Name of the edge to the foreign key.

    Attributes:
        id (Optional[str]): The ID of the related object.
        related_object (Optional[Model]): The related object instance.
    """

    sql_emitters = [RelatedObjectSQLEmitter]

    field_definitions = {
        "id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(
                target="un0.related_object.id",
                ondelete="CASCADE",
                to_edge="HAS_ID",
                from_edge="IS_ID_OF",
            ),
            primary_key=True,
            index=True,
            unique=True,
            nullable=False,
            doc="Primary Key",
        ),
    }

    id: Optional[str] = None
    related_object: Optional[Model] = None


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


class NameDescriptionMixin(NameMixin, DescriptionMixin):
    pass


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
            doc="Time the record was created",
            editable=False,
        ),
        "owned_by_id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(
                target="un0.user.id",
                ondelete="CASCADE",
                to_edge="OWNED_BY",
                from_edge="OWNS",
            ),
            index=True,
            doc="User that owns the record",
        ),
        "modified_at": FieldDefinition(
            data_type=TIMESTAMP(timezone=True),
            doc="Time the record was modified_at",
            editable=False,
        ),
        "modified_by_id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(
                target="un0.user.id",
                ondelete="CASCADE",
                to_edge="LAST_MODIFIED_BY",
                from_edge="LAST_MODIFIED",
            ),
            index=True,
            doc="User that last modified the record",
        ),
    }

    created_at: Optional[datetime.datetime] = None
    owned_by_id: Optional[str] = None
    owned_by: Optional[Model] = None
    modified_at: Optional[datetime.datetime] = None
    modified_by_id: Optional[str] = None
    modified_by: Optional[Model] = None


class SoftDeleteMixin(ModelMixin):
    """
    SoftDeleteMixin is a mixin class that adds soft delete functionality to a model.

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

    sql_emitters = [SoftDeleteSQLEmitter]
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
                to_edge="DELETED_BY",
                from_edge="DELETED",
            ),
            index=True,
            doc="User that deleted the record",
        ),
    }

    is_deleted: bool = False
    deleted_at: Optional[datetime.datetime] = None
    deleted_by_id: Optional[str] = None
    deleted_by: Optional[Model] = None


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
                to_edge="BELONGS_TO",
                from_edge="HAS",
            ),
            index=True,
            nullable=True,
            doc="Tenant to which the record belongs",
        ),
    }

    tenant_id: str
    tenant: Optional[Model] = None


class GroupMixin(ModelMixin):
    """
    GroupMixin is a mixin class that provides group-related fields and functionality to a model.

    Attributes:
        field_definitions (dict): A dictionary defining the group_id field with its properties,
            including data type, foreign key constraints, index, nullability, documentation, and
            edge names for relationships.
        group_id (str): The ID of the group to which the record belongs.
        group (Model): The group model instance associated with the group_id.
    """

    field_definitions = {
        "group_id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(
                target="un0.group.id",
                ondelete="CASCADE",
                to_edge="BELONGS_TO",
                from_edge="HAS",
            ),
            index=True,
            nullable=True,
            doc="Group to which the record belongs",
        ),
    }

    group_id: str
    group: Optional[Model] = None


class AuthMixin(RelatedObjectMixin, ActiveMixin, CreatedModifiedMixin, SoftDeleteMixin):
    pass


class DefaultRLSMixin(
    GroupMixin,
    TenantMixin,
    ActiveMixin,
    CreatedModifiedMixin,
    SoftDeleteMixin,
    RelatedObjectMixin,
    ImportMixin,
):
    pass
