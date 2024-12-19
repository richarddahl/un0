# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime
import textwrap

from typing import Type, Optional

from sqlalchemy import (
    text,
    Identity,
    Integer,
)
from sqlalchemy.dialects.postgresql import (
    BOOLEAN,
    ENUM,
    ARRAY,
    TEXT,
    VARCHAR,
    TIMESTAMP,
)

from un0.database.fields import (
    FKDefinition,
    UniqueDefinition,
    CheckDefinition,
    IndexDefinition,
    FieldDefinition,
)
from un0.database.models import Model
from un0.database.mixins import NameMixin, DescriptionMixin
from un0.database.enums import SQLOperation
from un0.database.sql_emitters import RecordVersionAuditSQL
from un0.relatedobjects.models import TableType
from un0.relatedobjects.mixins import RelatedObjectIdMixin
from un0.authorization.sql_emitters import UserRecordFieldAuditSQL
from un0.authorization.enums import TenantType
from un0.authorization.mixins import (
    TenantMixin,
    AuthorizationMixin,
    ActiveDeletedMixin,
    ImportMixin,
)
from un0.authorization.sql_emitters import (
    ValidateGroupInsert,
    InsertGroupForTenant,
    DefaultGroupTenant,
)
from un0.authorization.rls_sql_emitters import (
    RLSSQL,
    UserRLSSQL,
    TenantRLSSQL,
)


class Tenant(
    Model,
    AuthorizationMixin,
    NameMixin,
    schema_name="un0",
    table_name="tenant",
):
    """The Tenant model."""

    # name: str <- NameMixin
    # id: str <- AuthModelMixin
    # related_object: RelatedObject <- AuthModelMixin
    # active: bool <- AuthModelMixin
    # created_at: datetime <- AuthModelMixin
    # created_by: User <- AuthModelMixin
    # modified_at: datetime <- AuthModelMixin
    # modified_by: User <- AuthModelMixin
    # is_deleted: bool <- AuthModelMixin
    # deleted_at: datetime <- AuthModelMixin
    # deleted_by: User <- AuthModelMixin

    sql_emitters = [InsertGroupForTenant]

    constraint_definitions = [UniqueDefinition(columns=["name"], name="uq_tenant_name")]
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
    RelatedObjectIdMixin,
    ActiveDeletedMixin,
    ImportMixin,
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

    vertex_column = "id"
    sql_emitters = [UserRecordFieldAuditSQL, UserRLSSQL]
    constraint_definitions = [
        CheckDefinition(
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
        ),
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
            index=True,
        ),
        "full_name": FieldDefinition(
            data_type=TEXT,
            nullable=False,
        ),
        "default_group_id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key_definition=FKDefinition(
                target_column_name="un0.group.id",
                ondelete="CASCADE",
                edge_label="IS_DEFAULT_GROUP",
                reverse_edge_labels=["IS_DEFAULT_GROUP_FOR"],
            ),
            index=True,
            nullable=True,
            doc="Default group for the user",
        ),
        "is_superuser": FieldDefinition(
            data_type=BOOLEAN,
            server_default=text("false"),
            nullable=False,
        ),
        "is_tenant_admin": FieldDefinition(
            data_type=BOOLEAN,
            server_default=text("false"),
            nullable=False,
        ),
        "tenant_id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key_definition=FKDefinition(
                target_column_name="un0.tenant.id",
                ondelete="CASCADE",
                edge_label="WORKS_FOR",
                reverse_edge_labels=["HAS_EMPLOYEE"],
            ),
            index=True,
            doc="Tenant to which the user belongs",
        ),
        "created_at": FieldDefinition(
            data_type=TIMESTAMP(timezone=True),
            doc="Time the user was created",
            editable=False,
            nullable=False,
        ),
        "owned_by_id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key_definition=FKDefinition(
                target_column_name="un0.user.id",
                ondelete="CASCADE",
                edge_label="OWNED_BY",
                reverse_edge_labels=["OWNS"],
            ),
            index=True,
            nullable=True,  # Must be true for the first user
            doc="User that owns the user",
        ),
        "modified_at": FieldDefinition(
            data_type=TIMESTAMP(timezone=True),
            doc="Time the user was modified",
            editable=False,
            nullable=False,
        ),
        "modified_by_id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key_definition=FKDefinition(
                target_column_name="un0.user.id",
                ondelete="CASCADE",
                edge_label="LAST_MODIFIED_BY",
                reverse_edge_labels=["LAST_MODIFIED"],
            ),
            index=True,
            nullable=True,  # Must be true for the first user
            doc="User that last modified the user",
        ),
        "deleted_at": FieldDefinition(
            data_type=TIMESTAMP(timezone=True),
            doc="Time the user was deleted",
            editable=False,
            nullable=True,
        ),
        "deleted_by_id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key_definition=FKDefinition(
                target_column_name="un0.user.id",
                ondelete="CASCADE",
                edge_label="DELETED_BY",
                reverse_edge_labels=["DELETED"],
            ),
            index=True,
            nullable=True,
            doc="User that deleted the user",
        ),
    }

    # tenant_id: str <- TenantModelMixin
    # tenant: Tenant <- TenantModelMixin
    # id: str <- AuthModelMixin
    # related_object: RelatedObject <- AuthModelMixin
    # active: bool <- AuthModelMixin
    # created_at: datetime <- AuthModelMixin
    # created_by: User <- AuthModelMixin
    # modified_at: datetime <- AuthModelMixin
    # modified_by: User <- AuthModelMixin
    # is_deleted: bool <- AuthModelMixin
    # deleted_at: datetime <- AuthModelMixin
    # deleted_by: User <- AuthModelMixin

    email: Optional[str] = None
    handle: Optional[str] = None
    full_name: Optional[str] = None
    default_group_id: Optional[str] = None
    default_group: Optional[Type["Group"]] = None
    is_superuser: bool = False
    is_tenant_admin: bool = False
    tenant_id: Optional[str] = None
    tenant: Optional[Model] = None
    owns: Optional[list[Type[Model]]] = None
    last_modified: Optional[list[Type[Model]]] = None
    deleted: Optional[list[Type[Model]]] = None
    created_at: Optional[datetime.datetime] = None
    owned_by_id: Optional[str] = None
    owned_by: Optional[Model] = None
    modified_at: Optional[datetime.datetime] = None
    modified_by_id: Optional[str] = None
    modified_by: Optional[Model] = None

    def __str__(self) -> str:
        return self.handle


class TableOperation(
    Model,
    schema_name="un0",
    table_name="table_operation",
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
    Deleted automatically by the DB via the FKDefinition Constraints ondelete when a table_type is deleted.
    """

    constraint_definitions = [
        UniqueDefinition(
            columns=["table_type_id", "operations"], name="uq_tabletype_operations"
        )
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
            foreign_key_definition=FKDefinition(
                target_column_name="un0.table_type.id",
                ondelete="CASCADE",
                edge_label="HAS_TABLE_TYPE",
                reverse_edge_labels=["HAS_TABLE_PERMISSION"],
            ),
            index=True,
        ),
        "operations": FieldDefinition(
            data_type=ARRAY(
                ENUM(
                    SQLOperation,
                    name="sqloperation",
                    create_type=True,
                    schema="un0",
                )
            ),
            doc="Action that is permissible",
            index=True,
        ),
    }

    table_type_id: Optional[str] = None
    table_type: Optional[TableType] = None
    operation: Optional[list[SQLOperation]] = SQLOperation.SELECT

    def __str__(self) -> str:
        return f"{self.table_type} - {self.operation}"


class Role(
    Model,
    NameMixin,
    DescriptionMixin,
    AuthorizationMixin,
    TenantMixin,
    # DefaultRLSModelMixin,
    schema_name="un0",
    table_name="role",
):
    """
    Represents a role within the system, created by end user group admins.
    Roles enable the assignment of group permissions by functionality, department, etc., to users.
    """

    index_definitions = [
        IndexDefinition(name="ix_role_tenant_id_name", columns=["tenant_id", "name"])
    ]
    constraint_definitions = [
        UniqueDefinition(columns=["tenant_id", "name"], name="uq_role_tenant_name")
    ]

    # name: str <- NameDescriptionMixin
    # description: str <- NameDescriptionMixin
    # id: str <- DefaultRLSModelMixin
    # related_object: RelatedObject <- DefaultRLSModelMixin
    # active: bool <- DefaultRLSModelMixin
    # created_at: datetime <- DefaultRLSModelMixin
    # created_by: User <- DefaultRLSModelMixin
    # modified_at: datetime <- DefaultRLSModelMixin
    # modified_by: User <- DefaultRLSModelMixin
    # is_deleted: bool <- DefaultRLSModelMixin
    # deleted_at: datetime <- DefaultRLSModelMixin
    # deleted_by: User <- DefaultRLSModelMixin
    # tenant_id: str <- DefaultRLSModelMixin
    # tenant: Tenant <- DefaultRLSModelMixin


class RoleTableOperation(
    Model,
    schema_name="un0",
    table_name="role_table_operation",
):
    """
    Represents the operations permitted for a role/table combination.
    Created by end user group admins.
    """

    sql_emitters = [RecordVersionAuditSQL]
    field_definitions = {
        "role_id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key_definition=FKDefinition(
                target_column_name="un0.role.id",
                ondelete="CASCADE",
                edge_label="HAS_ROLE",
                reverse_edge_labels=["HAS_TABLE_OPERATION"],
            ),
            index=True,
            primary_key=True,
            doc="The applicable role",
        ),
        "table_operation_id": FieldDefinition(
            data_type=Integer,
            foreign_key_definition=FKDefinition(
                target_column_name="un0.table_operation.id",
                ondelete="CASCADE",
                edge_label="HAS_TABLE_OPERATION",
                reverse_edge_labels=["HAS_ROLE"],
            ),
            primary_key=True,
            index=True,
            doc="The applicable table operation",
        ),
    }

    role_id: Optional[str] = None
    role: Optional[Role] = None
    table_type_id: Optional[str] = None
    table_type: Optional[TableOperation] = None
    table_operations: Optional[list[SQLOperation]] = [SQLOperation.SELECT]

    def __str__(self) -> str:
        return f"{self.role} - {self.table_operations}"


class Group(
    Model,
    NameMixin,
    DescriptionMixin,
    TenantMixin,
    AuthorizationMixin,
    schema_name="un0",
    table_name="group",
):
    """
    Represents a group within the system, created by end user group admins.
    Groups enable the assignment of roles to users.
    """

    # sql_emitters = [ValidateGroupInsert, DefaultGroupTenant]
    index_definitions = [
        IndexDefinition(name="ix_group_name_tenant", columns=["name", "tenant_id"])
    ]
    constraint_definitions = [
        UniqueDefinition(columns=["name", "tenant_id"], name="uq_group_name_tenant")
    ]

    # name: str <- NameMixin
    # tenant_id: str <- TenantModelMixin
    # tenant: Tenant <- TenantModelMixin
    # id: str <- AuthModelMixin
    # related_object: RelatedObject <- AuthModelMixin
    # active: bool <- AuthModelMixin
    # created_at: datetime <- AuthModelMixin
    # created_by: User <- AuthModelMixin
    # modified_at: datetime <- AuthModelMixin
    # modified_by: User <- AuthModelMixin
    # is_deleted: bool <- AuthModelMixin
    # deleted_at: datetime <- AuthModelMixin
    # deleted_by: User <- AuthModelMixin


class UserGroupRole(
    Model,
    schema_name="un0",
    table_name="user_group_role",
):
    """
    Represents the roles assigned to a user for a group.
    Created by end user group admins.
    """

    sql_emitters = [RecordVersionAuditSQL]
    field_definitions = {
        "user_id": FieldDefinition(
            data_type=VARCHAR(26),
            foreign_key_definition=FKDefinition(
                target_column_name="un0.user.id",
                ondelete="CASCADE",
                edge_label="HAS_USER",
                reverse_edge_labels=["HAS_GROUP", "HAS_ROLE"],
            ),
            index=True,
        ),
        "group_id": FieldDefinition(
            data_type=VARCHAR(26),
            primary_key=True,
            foreign_key_definition=FKDefinition(
                target_column_name="un0.group.id",
                ondelete="CASCADE",
                edge_label="HAS_GROUP",
                reverse_edge_labels=["HAS_USER", "HAS_ROLE"],
            ),
            index=True,
        ),
        "role_id": FieldDefinition(
            data_type=VARCHAR(26),
            primary_key=True,
            foreign_key_definition=FKDefinition(
                target_column_name="un0.role.id",
                ondelete="CASCADE",
                edge_label="HAS_ROLE",
                reverse_edge_labels=["HAS_USER", "HAS_GROUP"],
            ),
            index=True,
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
