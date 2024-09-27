# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import textwrap
import datetime

from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.dialects.postgresql import ENUM, ARRAY

from un0.auth.enums import (
    TenantType,
    PermissionAction,
)
from un0.db import Base, BaseMixin, str_26, str_255  # type: ignore
from un0.rltd.models import RelatedObject, TableType


class Tenant(Base, BaseMixin):
    __tablename__ = "tenant"
    __table_args__ = (
        {
            "schema": "un0",
            "comment": "Application end-user tenants",
            "info": {"rls_policy": "superuser"},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=sa.func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_RELATED_OBJECT"},
    )
    name: Mapped[str_255] = mapped_column(unique=True, doc="Tenant name")
    tenant_type: Mapped[TenantType] = mapped_column(
        ENUM(TenantType, name="tenanttype", create_type=True, schema="un0"),
        server_default=TenantType.INDIVIDUAL.name,
        doc="Tenant type",
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        back_populates="tenant",
        foreign_keys="User.tenant_id",
        doc="Users that belong to the tenant",
    )

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<Tenant {self.name}>"


class User(Base):
    __tablename__ = "user"
    __table_args__ = (
        sa.CheckConstraint(
            textwrap.dedent(
                """
                is_superuser = 'false' AND default_group_id IS NOT NULL OR 
                is_superuser = 'true' AND default_group_id IS NULL AND
                is_superuser = 'false' AND is_tenant_admin = 'false' OR
                is_superuser = 'true' AND is_tenant_admin = 'false' OR
                is_superuser = 'false' AND is_tenant_admin = 'true'
            """
            ),
            name="ck_user_is_superuser",
        ),
        {
            "schema": "un0",
            "comment": "Application users",
            "info": {"rls_policy": "admin"},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=sa.func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_RELATED_OBJECT"},
    )
    email: Mapped[str_255] = mapped_column(
        unique=True, index=True, doc="Email address, used as login ID"
    )
    handle: Mapped[str_255] = mapped_column(
        unique=True, index=True, doc="User's displayed name and alternate login ID"
    )
    full_name: Mapped[str_255] = mapped_column(doc="User's full name")
    tenant_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey("un0.tenant.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
        info={"edge": "WORKS_FOR"},
    )
    default_group_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey("un0.group.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
        info={"edge": "HAS_DEFAULT_GROUP"},
    )
    is_superuser: Mapped[bool] = mapped_column(
        server_default=sa.text("false"), index=True, doc="Superuser status"
    )
    is_tenant_admin: Mapped[bool] = mapped_column(
        server_default=sa.text("false"), index=True, doc="Tenant admin status"
    )
    is_active: Mapped[bool] = mapped_column(
        server_default=sa.text("true"), doc="Active"
    )
    is_deleted: Mapped[bool] = mapped_column(
        server_default=sa.text("false"), doc="Deleted"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=sa.func.current_timestamp(),
        doc="Time the record was created",
    )
    owner_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_OWNED_BY"},
    )
    modified_at: Mapped[datetime.datetime] = mapped_column(
        doc="Time the record was last modified",
        server_default=sa.func.current_timestamp(),
    )
    modified_by_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "WAS_LAST_MODIFIED_BY"},
    )
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        doc="Time the record was deleted"
    )
    deleted_by_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "WAS_DELETED_BY"},
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship(
        back_populates="users",
        foreign_keys=[tenant_id],
        doc="Tenant the user belongs to",
    )
    default_group: Mapped["Group"] = relationship(
        back_populates="users_default_group",
        foreign_keys=[default_group_id],
        doc="Default group for the user",
    )
    # owner: Mapped["User"] = relationship(
    #    foreign_keys=[owner_id],
    #    doc="User that owns the record",
    # )
    # owned_users: Mapped[list["User"]] = relationship(
    #    primaryjoin="User.id == User.owner_id",
    #    doc="Users owned by the user",
    # )
    """
    modified_by: Mapped["User"] = relationship(
        back_populates="modified_users",
        foreign_keys=[modified_by_id],
        remote_side=[id],
        doc="User that last modified the record",
    )
    deleted_by: Mapped["User"] = relationship(
        back_populates="deleted_users",
        foreign_keys=[deleted_by_id],
        remote_side=[id],
        doc="User that deleted the record",
    )
    modified_users: Mapped[list["User"]] = relationship(
        back_populates="modified_by",
        foreign_keys=[id],
        remote_side=[modified_by_id],
        doc="Users modified by the user",
    )
    deleted_users: Mapped[list["User"]] = relationship(
        back_populates="deleted_by",
        foreign_keys=[id],
        remote_side=[deleted_by_id],
        doc="Users deleted by the user",
    )
    """

    def __str__(self) -> str:
        return self.email

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class TablePermission(Base):
    __tablename__ = "table_permission"
    __table_args__ = (
        sa.UniqueConstraint(
            "permissive_table_type_id",
            "actions",
            name="uq_permissive_table_type_permission_actions",
        ),
        {
            "schema": "un0",
            "comment": """
                Permissions for each table.
                Created automatically by the DB via a trigger when a Table using role access is created.
                Records are created for each table with the following combinations of permissions:
                    [SELECT]
                    [SELECT, INSERT]
                    [SELECT, UPDATE]
                    [SELECT, INSERT, UPDATE]
                    [SELECT, INSERT, UPDATE, DELETE]
                Deleted automatically by the DB via the FK Constraints ondelete when a table_type is deleted.
            """,
            "info": {"rls_policy": "superuser"},
        },
    )
    id: Mapped[int] = mapped_column(sa.Identity(), primary_key=True)
    permissive_table_type_id: Mapped[TableType] = mapped_column(
        sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "HAS_PERMISSIVE_ACTIONS_FOR_TABLE_TYPE"},
    )
    actions: Mapped[list[PermissionAction]] = mapped_column(
        ARRAY(
            ENUM(
                PermissionAction,
                name="permission_name",
                create_type=True,
                schema="un0",
            )
        ),
        doc="Actions that are permissible",
    )

    def __str__(self) -> str:
        return f"{self.table_type} - {self.actions}"

    def __repr__(self) -> str:
        return f"<TablePermission {self.table_type} - {self.actions}>"


class Role(Base, BaseMixin):
    __tablename__ = "role"
    __table_args__ = (
        sa.Index("ix_role_tenant_id_name", "tenant_id", "name"),
        sa.UniqueConstraint("tenant_id", "name"),
        {
            "comment": """
                Roles, created by end user group admins, enable assignment of group_permissions
                by functionality, department, etc... to users.
            """,
            "schema": "un0",
            "info": {"rls_policy": "admin"},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=sa.func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_RELATED_OBJECT"},
    )
    tenant_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        info={"edge": "BELONGS_TO_CUSTOMER"},
    )
    name: Mapped[str_255] = mapped_column(doc="Role name")
    description: Mapped[str] = mapped_column(doc="Role description")

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class RoleTablePermission(Base):
    __tablename__ = "role_table_permission"
    __table_args__ = (
        {
            "comment": """
                Assigned by tenant_admin users to assign roles for groups to users based on organization requirements.
            """,
            "schema": "un0",
            "info": {"edge": "HAS_ROLE_TABLE_PERMISSION", "rls_policy": "none"},
        },
    )

    # Columns
    role_id: Mapped[int] = mapped_column(
        sa.ForeignKey("un0.role.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        info={"edge": "HAS_ROLE"},
    )
    table_permission_id: Mapped[int] = mapped_column(
        sa.ForeignKey("un0.table_permission.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        info={"edge": "HAS_TABLE_PERMISSION"},
    )

    def __str__(self) -> str:
        return f"{self.role_id} - {self.table_permission_id}"

    def __repr__(self) -> str:
        return f"<RoleTablePermission {self.role_id} - {self.table_permission_id}>"


class Group(Base, BaseMixin):
    __tablename__ = "group"
    __table_args__ = (
        sa.Index("ix_group_tenant_id_name", "tenant_id", "name"),
        sa.UniqueConstraint("tenant_id", "name"),
        {
            "comment": "Application end-user groups",
            "schema": "un0",
            "info": {"rls_policy": "admin"},
        },
    )

    # Columns

    id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        server_default=sa.func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_RELATED_OBJECT"},
    )
    tenant_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.tenant.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "BELONGS_TO_CUSTOMER"},
    )
    name: Mapped[str_255] = mapped_column(doc="Group name")

    # Relationships
    users_default_group: Mapped[list["User"]] = relationship(
        back_populates="default_group",
        foreign_keys="User.default_group_id",
        doc="Users that have this group as their default group",
    )

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<Group {self.name}>"


class UserGroupRole(Base, BaseMixin):
    __tablename__ = "user_group_role"
    __table_args__ = (
        {
            "comment": """
                Assigned by tenant_admin users to assign roles for groups to users based on organization requirements.
            """,
            "schema": "un0",
            "info": {"rls_policy": "admin", "edge": "HAS_USER_GROUP_ROLE"},
        },
    )

    # Columns
    user_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        primary_key=True,
        info={"edge": "HAS_USER"},
    )
    group_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.group.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        primary_key=True,
        info={"edge": "HAS_GROUP"},
    )
    role_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.role.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        primary_key=True,
        info={"edge": "HAS_ROLE"},
    )
