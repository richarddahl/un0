# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap

from typing import Type, Optional

from sqlalchemy import (
    text,
    Identity,
    Integer,
)
from sqlalchemy.dialects.postgresql import BOOLEAN, ENUM, ARRAY

from un0.db.fields import (
    FK,
    UQ,
    CK,
    IX,
    FieldDefinition,
)
from un0.db.models import Model
from un0.db.model_mixins import (
    RelatedObjectMixin,
    ActiveMixin,
    TrashMixin,
    CreatedModifiedMixin,
    NameMixin,
    TenantMixin,
    DescriptionMixin,
)
from un0.db.types import (
    str_26,
    str_128,
    str_255,
)
from un0.auth.enums import (
    TenantType,
    PermissionAction,
)
from un0.db.sql_emitters import (
    DefaultAuditSQLEmitter,
    UserRLSSQLEmitter,
    AdminRLSSQLEmitter,
)
from un0.rltd.models import TableType


class Tenant(
    Model,
    RelatedObjectMixin,
    ActiveMixin,
    TrashMixin,
    CreatedModifiedMixin,
    NameMixin,
    db_schema="un0",
    table_name="tenant",
):
    """The Tenant model."""

    constraints = [
        UQ(
            columns=["name"],
            name="uq_tenant_name",
        ),
    ]
    sql_emitters = [
        DefaultAuditSQLEmitter,
        AdminRLSSQLEmitter,
    ]
    field_definitions = {
        "tenant_type": FieldDefinition(
            data_type=ENUM(
                TenantType,
                name="tenanttype",
                create_type=True,
                schema="un0",
            ),
            nullable=False,
            index=True,
            server_default=TenantType.INDIVIDUAL.name,
            doc="The type of Tenant: One of Individual, Business, Corporate, or Enterprise",
        )
    }
    tenant_type: TenantType

    def __str__(self) -> str:
        return f"{self.name} ({self.tenant_type})"


class User(
    Model,
    RelatedObjectMixin,
    ActiveMixin,
    TrashMixin,
    CreatedModifiedMixin,
    TenantMixin,
    db_schema="un0",
    table_name="user",
):
    """
    User Model

    Attributes:
        email (str): The email address of the user. Must be unique and not nullable.
        handle (str): The handle or username of the user. Must not be nullable.
        full_name (str): The full name of the user. Must not be nullable.
        default_group_id (Optional[str]): The ID of the default group for the user. Can be null.
        default_group (Optional[Type["Group"]]): The default group object for the user.
        is_superuser (bool): Indicates if the user is a superuser. Defaults to False.
        is_tenant_admin (bool): Indicates if the user is a tenant admin. Defaults to False.

    Constraints:
        ck_user_is_superuser: Ensures the logical consistency of the is_superuser and default_group_id fields.

    SQL Emitters:
        DefaultAuditSQLEmitter: Emitter for default audit SQL.
        UserRLSSQLEmitter: Emitter for user RLS SQL.

    Field Definitions:
        email: Field definition for the email attribute.
        handle: Field definition for the handle attribute.
        full_name: Field definition for the full_name attribute.
        default_group_id: Field definition for the default_group_id attribute.
        is_superuser: Field definition for the is_superuser attribute.
        is_tenant_admin: Field definition for the is_tenant_admin attribute.

    Methods:
        __str__: Returns the handle of the user as the string representation.
    """

    constraints = [
        CK(
            expression=textwrap.dedent(
                """
                (is_superuser = 'false' AND default_group_id IS NOT NULL) OR
                (is_superuser = 'true' AND default_group_id IS NULL) AND
                (is_superuser = 'false' AND is_tenant_admin = 'false') OR
                (is_superuser = 'true' AND is_tenant_admin = 'false') OR
                (is_superuser = 'false' AND is_tenant_admin = 'true')
                """
            ),
            name="ck_user_is_superuser",
        )
    ]
    sql_emitters = [
        DefaultAuditSQLEmitter,
        UserRLSSQLEmitter,
    ]
    field_definitions = {
        "email": FieldDefinition(
            data_type=str_128,
            unique=True,
            index=True,
            nullable=False,
        ),
        "handle": FieldDefinition(
            data_type=str_128,
            nullable=False,
        ),
        "full_name": FieldDefinition(
            data_type=str_255,
            nullable=False,
        ),
        "default_group_id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(
                target="un0.group.id",
                ondelete="CASCADE",
            ),
            index=True,
            nullable=True,
            doc="Default group for the user",
            to_fk_edge_name="IS_DEFAULT",
            from_fk_edge_name="IS_DEFAULT_FOR",
        ),
        "is_superuser": FieldDefinition(
            data_type=BOOLEAN,
            server_default=text("false"),
        ),
        "is_tenant_admin": FieldDefinition(
            data_type=BOOLEAN,
            server_default=text("false"),
        ),
    }

    email: str
    handle: str
    full_name: str
    default_group_id: Optional[str] = None
    default_group: Optional[Type["Group"]]
    is_superuser: bool = False
    is_tenant_admin: bool = False

    def __str__(self) -> str:
        return self.handle


class TablePermission(
    Model,
    db_schema="un0",
    table_name="table_permission",
):
    """
    Permissions for each table.
    Created automatically by the DB via a trigger when a Table using role access is created.
    Records are created for each table with the following combinations of permissions:
        [SELECT]
        [SELECT, INSERT]
        [SELECT, UPDATE]
        [SELECT, INSERT, UPDATE]
        [SELECT, INSERT, UPDATE, DELETE]
    Deleted automatically by the DB via the FK Constraints ondelete when a tabletype is deleted.
    """

    constraints = [
        UQ(
            columns=["table_type_id", "actions"],
            name="uq_tabletype_actions",
        ),
    ]
    sql_emitters = (DefaultAuditSQLEmitter,)
    field_definitions = {
        "id": FieldDefinition(
            data_type=Identity(start=1, cycle=False),
            primary_key=True,
            index=True,
            doc="Primary Key",
            autoincrement=True,
        ),
        "table_type_id": FieldDefinition(
            data_type=Integer,
            foreign_key=FK(
                target="un0.table_type.id",
                ondelete="CASCADE",
            ),
            index=True,
            to_fk_edge_name="HAS_TABLE_TYPE",
            from_fk_edge_name="HAS_TABLE_PERMISSION",
        ),
        "actions": FieldDefinition(
            data_type=ARRAY(
                ENUM(
                    PermissionAction,
                    name="permission",
                    create_type=True,
                    schema="un0",
                )
            ),
            doc="Actions that are permissible",
        ),
    }

    table_type_id: int
    table_type: TableType
    actions: PermissionAction

    def __str__(self) -> str:
        return f"{self.table_type} - {self.actions}"


class Role(
    Model,
    RelatedObjectMixin,
    ActiveMixin,
    TrashMixin,
    CreatedModifiedMixin,
    TenantMixin,
    NameMixin,
    DescriptionMixin,
    db_schema="un0",
    table_name="role",
):
    """
    Represents a role within the system, created by end user group admins.
    Roles enable the assignment of group permissions by functionality, department, etc., to users.
    """

    sql_emitters = [DefaultAuditSQLEmitter]
    indices = [
        IX(
            name="ix_role_tenant_id_name",
            columns=["tenant_id", "name"],
        ),
    ]
    constraints = [
        UQ(
            columns=["tenant_id", "name"],
            name="uq_role_tenant_name",
        ),
    ]


class RoleTablePermission(
    Model,
    db_schema="un0",
    table_name="role_table_permission",
):
    """
    Represents the permissions assigned to a role for a table.
    Created by end user group admins.
    """

    sql_emitters = [DefaultAuditSQLEmitter]
    field_definitions = {
        "role_id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(target="un0.role.id", ondelete="CASCADE"),
            index=True,
            to_fk_edge_name="HAS_ROLE",
        ),
        "table_permission_id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(target="un0.table_permission.id", ondelete="CASCADE"),
            index=True,
            to_fk_edge_name="HAS_TABLE_PERMISSION",
        ),
    }

    role_id: str
    role: Role
    table_permission_id: str
    table_permission: TablePermission

    def __str__(self) -> str:
        return f"{self.role} - {self.table_permission}"


class Group(
    Model,
    RelatedObjectMixin,
    ActiveMixin,
    TrashMixin,
    CreatedModifiedMixin,
    TenantMixin,
    NameMixin,
    db_schema="un0",
    table_name="group",
):
    """
    Represents a group within the system, created by end user group admins.
    Groups enable the assignment of roles to users.
    """

    indices = [
        IX(
            name="ix_group_name_tenant",
            columns=["name", "tenant_id"],
        ),
    ]
    constraints = [
        UQ(
            columns=["name", "tenant_id"],
            name="uq_group_name_tenant",
        ),
    ]


class UserGroupRole(
    Model,
    db_schema="un0",
    table_name="user_group_role",
):
    """
    Represents the roles assigned to a user for a group.
    Created by end user group admins.
    """

    field_definitions = {
        "user_id": FieldDefinition(
            data_type=str_26,
            foreign_key=FK(
                target="un0.user.id",
                ondelete="CASCADE",
            ),
            index=True,
            to_fk_edge_name="HAS_USER",
        ),
        "group_id": FieldDefinition(
            data_type=str_26,
            primary_key=True,
            foreign_key=FK(
                target="un0.group.id",
                ondelete="CASCADE",
            ),
            index=True,
            to_fk_edge_name="HAS_GROUP",
        ),
        "role_id": FieldDefinition(
            data_type=str_26,
            primary_key=True,
            foreign_key=FK(
                target="un0.role.id",
                ondelete="CASCADE",
            ),
            index=True,
            to_fk_edge_name="HAS_ROLE",
        ),
    }

    user_id: str
    user: User
    group_id: str
    group: Group
    role_id: str
    role: Role

    def __str__(self) -> str:
        return f"{self.user} - {self.group} - {self.role}"
