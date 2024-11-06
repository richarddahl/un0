# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

import datetime

from typing import Optional

from sqlalchemy.dialects.postgresql import TIMESTAMP, VARCHAR

from pydantic.dataclasses import dataclass

from un0.database.models import Model
from un0.database.sql_emitters import SQLEmitter
from un0.database.fields import FieldDefinition, FK
from un0.database.mixins import (
    FieldMixin,
    ActiveDeletedMixin,
    ImportMixin,
)
from un0.relatedobjects.mixins import RelatedObjectIdMixin
from un0.authorization.sql_emitters import RecordFieldAuditSQL


class RecordFieldAuditMixin(FieldMixin):
    sql_emitters = [RecordFieldAuditSQL]
    field_definitions = {
        "created_at": FieldDefinition(
            data_type=TIMESTAMP(timezone=True),
            doc="Time the record was created",
            editable=False,
            nullable=False,
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
            nullable=False,
            doc="User that owns the record",
        ),
        "modified_at": FieldDefinition(
            data_type=TIMESTAMP(timezone=True),
            doc="Time the record was modified_at",
            editable=False,
            nullable=False,
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
            nullable=False,
            doc="User that last modified the record",
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

    created_at: Optional[datetime.datetime] = None
    owned_by_id: Optional[str] = None
    owned_by: Optional[Model] = None
    modified_at: Optional[datetime.datetime] = None
    modified_by_id: Optional[str] = None
    modified_by: Optional[Model] = None
    deleted_at: Optional[datetime.datetime] = None
    deleted_by_id: Optional[str] = None
    deleted_by: Optional[Model] = None


@dataclass
class DefaultTenantSQL(SQLEmitter):
    def emit_sql(self) -> str:
        function_string = textwrap.dedent(
            """
            DECLARE
                tenant_id TEXT := current_setting('rls_var.tenant_id', true);
            BEGIN
                IF tenant_id IS NULL THEN
                    RAISE EXCEPTION 'tenant_id is NULL';
                END IF;

                NEW.tenant_id := tenant_id;

                RETURN NEW;
            END;
            """
        )
        return self.create_sql_function(
            "set_tenant_id",
            function_string,
            timing="BEFORE",
            operation="INSERT",
            include_trigger=True,
            db_function=False,
        )


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

    sql_emitters = [DefaultTenantSQL]

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
            nullable=False,
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
            nullable=False,
            doc="Group to which the record belongs",
        ),
    }

    group_id: Optional[str] = None
    group: Optional[Model] = None


class AuthorizationMixin(
    RelatedObjectIdMixin,
    ActiveDeletedMixin,
    ImportMixin,
):
    pass


class RLSMixin(
    RelatedObjectIdMixin,
    ActiveDeletedMixin,
    GroupMixin,
    TenantMixin,
    ImportMixin,
):
    pass
