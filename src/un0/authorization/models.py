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
from sqlalchemy.dialects.postgresql import BOOLEAN, ENUM, ARRAY, TEXT, VARCHAR

from un0.database.fields import (
    FK,
    UQ,
    CK,
    IX,
    FieldDefinition,
)
from un0.database.models import Model
from un0.database.mixins import NameMixin, NameDescriptionMixin
from un0.database.enums import SQLOperation
from un0.database.sql_emitters import EnableDefaultAuditSQL
from un0.relatedobjects.models import TableType
from un0.relatedobjects.sql_emitters import SetRelatedObjectIDSQL
from un0.authorization.enums import TenantType
from un0.authorization.mixins import TenantMixin, AuthMixin
from un0.authorization.sql_emitters import (
    CreatedModifiedFnctnSQL,
    SetDefaultTenantSQL,
)
from un0.authorization.rls_sql_emitters import (
    RLSSQL,
    TenantRLSSQL,
)


class Tenant(
    Model,
    NameMixin,
    AuthMixin,
    schema_name="un0",
    table_name="tenant",
):
    """The Tenant model."""

    # name: str <- NameMixin
    # id: str <- AuthFieldMixin
    # related_object: RelatedObject <- AuthFieldMixin
    # active: bool <- AuthFieldMixin
    # created_at: datetime <- AuthFieldMixin
    # created_by: User <- AuthFieldMixin
    # modified_at: datetime <- AuthFieldMixin
    # modified_by: User <- AuthFieldMixin
    # is_deleted: bool <- AuthFieldMixin
    # deleted_at: datetime <- AuthFieldMixin
    # deleted_by: User <- AuthFieldMixin

    # sql_emitters = [EnableDefaultAuditSQL, TenantRLSSQL]
    constraints = [UQ(columns=["name"], name="uq_tenant_name")]
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
    tenant_type: Optional[TenantType] = None

    def __str__(self) -> str:
        return f"{self.name} ({self.tenant_type})"


class User(
    Model,
    TenantMixin,
    AuthMixin,
    schema_name="un0",
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
        UserRLSSQL: Emitter for user RLS SQL.

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

    sql_emitters = [
        # CreatedModifiedFnctnSQL,
        EnableDefaultAuditSQL,
        SetRelatedObjectIDSQL,
        # UserRLSSQL,
    ]
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
    field_definitions = {
        "email": FieldDefinition(
            data_type=TEXT,
            unique=True,
            index=True,
            nullable=False,
        ),
        "handle": FieldDefinition(
            data_type=TEXT,
            nullable=False,
        ),
        "full_name": FieldDefinition(
            data_type=TEXT,
            nullable=False,
        ),
        "default_group_id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key=FK(
                target="un0.group.id",
                ondelete="CASCADE",
                to_edge="IS_DEFAULT",
                from_edge="IS_DEFAULT_FOR",
            ),
            index=True,
            nullable=True,
            doc="Default group for the user",
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

    # tenant_id: str <- TenantFieldMixin
    # tenant: Tenant <- TenantFieldMixin
    # id: str <- AuthFieldMixin
    # related_object: RelatedObject <- AuthFieldMixin
    # active: bool <- AuthFieldMixin
    # created_at: datetime <- AuthFieldMixin
    # created_by: User <- AuthFieldMixin
    # modified_at: datetime <- AuthFieldMixin
    # modified_by: User <- AuthFieldMixin
    # is_deleted: bool <- AuthFieldMixin
    # deleted_at: datetime <- AuthFieldMixin
    # deleted_by: User <- AuthFieldMixin

    email: Optional[str] = None
    handle: Optional[str] = None
    full_name: Optional[str] = None
    default_group_id: Optional[str] = None
    default_group: Optional[Type["Group"]] = None
    is_superuser: bool = False
    is_tenant_admin: bool = False
    owns: Optional[list[Type[Model]]] = None
    last_modified: Optional[list[Type[Model]]] = None
    deleted: Optional[list[Type[Model]]] = None

    def __str__(self) -> str:
        return self.handle


class TablePermission(
    Model,
    schema_name="un0",
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
    Deleted automatically by the DB via the FK Constraints ondelete when a table_type is deleted.
    """

    sql_emitters = []
    constraints = [
        UQ(columns=["table_type_id", "actions"], name="uq_tabletype_actions")
    ]
    field_definitions = {
        "id": FieldDefinition(
            data_type=Integer,
            fnct=Identity(start=1, cycle=False),
            primary_key=True,
            index=True,
            doc="Primary Key",
        ),
        "table_type_id": FieldDefinition(
            data_type=Integer,
            foreign_key=FK(
                target="un0.table_type.id",
                ondelete="CASCADE",
                to_edge="HAS_TABLE_TYPE",
                from_edge="HAS_TABLE_PERMISSION",
            ),
            index=True,
        ),
        "actions": FieldDefinition(
            data_type=ARRAY(
                ENUM(
                    SQLOperation,
                    name="sqloperation",
                    create_type=True,
                    schema="un0",
                )
            ),
            doc="Actions that are permissible",
        ),
    }

    table_type_id: Optional[str] = None
    table_type: Optional[TableType] = None
    actions: Optional[list[SQLOperation]] = SQLOperation.SELECT

    def __str__(self) -> str:
        return f"{self.table_type} - {self.actions}"


class Role(
    Model,
    NameDescriptionMixin,
    AuthMixin,
    TenantMixin,
    # DefaultRLSFieldMixin,
    schema_name="un0",
    table_name="role",
):
    """
    Represents a role within the system, created by end user group admins.
    Roles enable the assignment of group permissions by functionality, department, etc., to users.
    """

    # sql_emitters = [AuditModelSQLEmitter, AdminRLSSQL]
    indices = [IX(name="ix_role_tenant_id_name", columns=["tenant_id", "name"])]
    constraints = [UQ(columns=["tenant_id", "name"], name="uq_role_tenant_name")]

    # name: str <- NameDescriptionMixin
    # description: str <- NameDescriptionMixin
    # id: str <- DefaultRLSFieldMixin
    # related_object: RelatedObject <- DefaultRLSFieldMixin
    # active: bool <- DefaultRLSFieldMixin
    # created_at: datetime <- DefaultRLSFieldMixin
    # created_by: User <- DefaultRLSFieldMixin
    # modified_at: datetime <- DefaultRLSFieldMixin
    # modified_by: User <- DefaultRLSFieldMixin
    # is_deleted: bool <- DefaultRLSFieldMixin
    # deleted_at: datetime <- DefaultRLSFieldMixin
    # deleted_by: User <- DefaultRLSFieldMixin
    # tenant_id: str <- DefaultRLSFieldMixin
    # tenant: Tenant <- DefaultRLSFieldMixin


class RoleTablePermission(
    Model,
    schema_name="un0",
    table_name="role_table_permission",
):
    """
    Represents the permissions assigned to a role for a table.
    Created by end user group admins.
    """

    sql_emitters = [EnableDefaultAuditSQL]
    field_definitions = {
        "role_id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key=FK(
                target="un0.role.id",
                ondelete="CASCADE",
                to_edge="HAS_ROLE",
            ),
            index=True,
        ),
        "table_permission_id": FieldDefinition(
            data_type=Integer,
            foreign_key=FK(
                target="un0.table_permission.id",
                ondelete="CASCADE",
                to_edge="HAS_TABLE_PERMISSION",
            ),
            index=True,
        ),
    }

    role_id: Optional[str] = None
    role: Optional[Role] = None
    table_permission_id: Optional[str] = None
    table_permission: Optional[TablePermission] = None

    def __str__(self) -> str:
        return f"{self.role} - {self.table_permission}"


class Group(
    Model,
    NameDescriptionMixin,
    TenantMixin,
    AuthMixin,
    schema_name="un0",
    table_name="group",
):
    """
    Represents a group within the system, created by end user group admins.
    Groups enable the assignment of roles to users.
    """

    # sql_emitters = [AuditModelSQLEmitter, ValidateGroupInsertSQLEmitter]
    indices = [IX(name="ix_group_name_tenant", columns=["name", "tenant_id"])]
    constraints = [UQ(columns=["name", "tenant_id"], name="uq_group_name_tenant")]

    # name: str <- NameMixin
    # tenant_id: str <- TenantFieldMixin
    # tenant: Tenant <- TenantFieldMixin
    # id: str <- AuthFieldMixin
    # related_object: RelatedObject <- AuthFieldMixin
    # active: bool <- AuthFieldMixin
    # created_at: datetime <- AuthFieldMixin
    # created_by: User <- AuthFieldMixin
    # modified_at: datetime <- AuthFieldMixin
    # modified_by: User <- AuthFieldMixin
    # is_deleted: bool <- AuthFieldMixin
    # deleted_at: datetime <- AuthFieldMixin
    # deleted_by: User <- AuthFieldMixin


class UserGroupRole(
    Model,
    schema_name="un0",
    table_name="user_group_role",
):
    """
    Represents the roles assigned to a user for a group.
    Created by end user group admins.
    """

    sql_emitters = [EnableDefaultAuditSQL]
    field_definitions = {
        "user_id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key=FK(
                target="un0.user.id",
                ondelete="CASCADE",
            ),
            index=True,
            to_edge="HAS_USER",
        ),
        "group_id": FieldDefinition(
            data_type=VARCHAR(26),
            primary_key=True,
            foreign_key=FK(
                target="un0.group.id",
                ondelete="CASCADE",
            ),
            index=True,
            to_edge="HAS_GROUP",
        ),
        "role_id": FieldDefinition(
            data_type=VARCHAR(26),
            primary_key=True,
            foreign_key=FK(
                target="un0.role.id",
                ondelete="CASCADE",
            ),
            index=True,
            to_edge="HAS_ROLE",
        ),
    }

    user_id: Optional[str] = None
    user: Optional[User] = None
    group_id: Optional[str] = None
    group: Optional[Group] = None
    role_id: Optional[str] = None
    role: Optional[Role] = None

    def __str__(self) -> str:
        return f"{self.user} - {self.group} - {self.role}"
