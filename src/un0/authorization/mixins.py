# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime

from typing import Optional

from sqlalchemy import text, String, TEXT
from sqlalchemy.dialects.postgresql import TIMESTAMP, BOOLEAN, VARCHAR

from un0.database.models import Model
from un0.database.fields import FieldDefinition, FK
from un0.database.mixins import FieldMixin, ActiveMixin, TableTypeMixin, ImportMixin
from un0.relatedobjects.mixins import RelatedObjectIdMixin
from un0.authorization.sql_emitters import (
    CreatedModifiedFnctnSQL,
    CreatedModifiedTrggrSQL,
    SoftDeleteFnctnSQL,
    SoftDeleteTrggrSQL,
    SetDefaultTenantSQL,
)


class CreatedModifiedMixin(FieldMixin):
    """
    FieldMixin class that adds created and modified timestamp fields, along with ownership information to a model.

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

    sql_emitters = [CreatedModifiedFnctnSQL, CreatedModifiedTrggrSQL]
    field_definitions = {
        "created_at": FieldDefinition(
            data_type=TIMESTAMP(timezone=True),
            doc="Time the record was created",
            editable=False,
        ),
        "owned_by_id": FieldDefinition(
            data_type=VARCHAR(26),
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
            data_type=VARCHAR(26),
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


class SoftDeleteMixin(FieldMixin):
    """
    SoftDeleteFieldMixin is a mixin class that adds soft delete functionality to a model.

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

    sql_emitters = [SoftDeleteFnctnSQL, SoftDeleteTrggrSQL]
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
            data_type=VARCHAR(26),
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


class TenantMixin(FieldMixin):
    """
    TenantFieldMixin is a mixin class that provides tenant-related fields and functionality to a model.

    Attributes:
        field_definitions (dict): A dictionary defining the tenant_id field with its properties,
            including data type, foreign key constraints, index, nullability, documentation, and
            edge names for relationships.
        tenant_id (str): The ID of the tenant to which the record belongs.
        tenant (Model): The tenant model instance associated with the tenant_id.
    """

    sql_emitters = [SetDefaultTenantSQL]

    field_definitions = {
        "tenant_id": FieldDefinition(
            data_type=VARCHAR(26),
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

    tenant_id: Optional[str] = None
    tenant: Optional[Model] = None


class GroupMixin(FieldMixin):
    """
    GroupFieldMixin is a mixin class that provides group-related fields and functionality to a model.

    Attributes:
        field_definitions (dict): A dictionary defining the group_id field with its properties,
            including data type, foreign key constraints, index, nullability, documentation, and
            edge names for relationships.
        group_id (str): The ID of the group to which the record belongs.
        group (Model): The group model instance associated with the group_id.
    """

    field_definitions = {
        "group_id": FieldDefinition(
            data_type=VARCHAR(26),
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

    group_id: Optional[str] = None
    group: Optional[Model] = None


class AuthMixin(
    TableTypeMixin,
    RelatedObjectIdMixin,
    ActiveMixin,
    CreatedModifiedMixin,
    SoftDeleteMixin,
):
    pass


# class DefaultRLSMixin(
#    RelatedObjectIdMixin,
#    GroupMixin,
#    TenantMixin,
#    ActiveMixin,
#    CreatedModifiedMixin,
#    SoftDeleteMixin,
#    ImportMixin,
# ):
#    pass
