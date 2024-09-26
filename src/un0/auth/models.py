# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import textwrap

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
    name: Mapped[str_255] = mapped_column(unique=True, doc="Tenant name")
    tenant_type: Mapped[TenantType] = mapped_column(
        ENUM(TenantType, name="tenanttype", create_type=True, schema="un0"),
        server_default=TenantType.INDIVIDUAL.name,
        doc="Tenant type",
    )

    # Relationships
    # related_object: Mapped[list[RelatedObject]] = relationship(
    #    viewonly=True,
    #    doc="Related objects assigned to the tenant",
    # )
    # users: Mapped[list["User"]] = relationship(
    #    back_populates="tenant",
    #    doc="Users assigned to the tenant",
    # )
    # roles: Mapped[list["Role"]] = relationship(
    #    back_populates="tenant",
    #    doc="Roles assigned to the tenant",
    # )
    # groups: Mapped[list["Group"]] = relationship(
    #    back_populates="tenant",
    #    doc="Groups assigned to the tenant",
    # )
    # queries: Mapped[list["Query"]] = relationship(
    #    back_populates="tenant",
    #    doc="Queries assigned to the tenant",
    # )


class User(Base, BaseMixin):
    __tablename__ = "user"
    __table_args__ = (
        sa.CheckConstraint(
            textwrap.dedent(
                """
                --is_superuser = 'false' AND default_group_id IS NOT NULL OR 
                --is_superuser = 'true' AND default_group_id IS NULL AND
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

    # Relationships
    # tenant: Mapped[Tenant] = relationship(
    #    back_populates="users",
    #    doc="Tenants to which the user is assigned",
    # )
    # default_group: Mapped["Group"] = relationship(
    #    back_populates="users",
    #    doc="User's default group, used as default for creating new objects",
    # )
    # user_group_role: Mapped[list["UserGroupRole"]] = relationship(
    #    back_populates="user",
    #    doc="Roles assigned to the user for a group",
    # )
    def __str__(self) -> str:
        return self.email

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class TablePermission(Base):
    __tablename__ = "table_permission"
    __table_args__ = (
        sa.UniqueConstraint(
            "table_type_id", "actions", name="uq_table_type_permission_actions"
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
    table_type_id: Mapped[TableType] = mapped_column(
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

    # Relationships
    # table_type: Mapped["TableType"] = relationship(
    #    back_populates="table_permissions",
    #    foreign_keys=[table_type_id],
    #    doc="Table type to which the actions are permissible",
    # )
    # role_table_permission: Mapped[list["RoleTablePermission"]] = relationship(
    #    back_populates="table_permission",
    #    doc="Roles containing the table permission",
    # )

    def __str__(self) -> str:
        return f"{self.table_type} - {self.actions}"


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
    tenant_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        info={"edge": "BELONGS_TO_CUSTOMER"},
    )
    name: Mapped[str_255] = mapped_column(doc="Role name")
    description: Mapped[str] = mapped_column(doc="Role description")

    # Relationships
    # tenant: Mapped["Tenant"] = relationship(
    #    back_populates="roles",
    #    doc="Tenant to which the role belongs",
    # )
    # user_group_role: Mapped[list["UserGroupRole"]] = relationship(
    #    back_populates="role",
    #    doc="Roles assigned to the user for a group",
    # )
    # role_table_permission: Mapped[list["RoleTablePermission"]] = relationship(
    #    back_populates="role",
    #    doc="Table permissions assigned to the role",
    # )


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

    # Relationships
    # role: Mapped[Role] = relationship(back_populates="role_table_permission")
    # table_permission: Mapped[TablePermission] = relationship(
    #    back_populates="role_table_permission"
    # )


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

    tenant_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.tenant.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "BELONGS_TO_CUSTOMER"},
    )
    name: Mapped[str_255] = mapped_column(doc="Group name")

    # Relationships
    # tenant: Mapped[list["Tenant"]] = relationship(
    #    back_populates="groups",
    #    doc="Tenant to which the group belongs",
    # )
    # users: Mapped[list["User"]] = relationship(
    #    back_populates="default_group",
    #    doc="Users assigned to the group",
    # )
    # user_group_role: Mapped[list["UserGroupRole"]] = relationship(
    #    back_populates="group",
    #    doc="Roles assigned to the user for a group",
    # )


class UserGroupRole(Base, BaseMixin):
    __tablename__ = "user_group_role"
    __table_args__ = (
        {
            "comment": """
                Assigned by tenant_admin users to assign roles for groups to users based on organization requirements.
            """,
            "schema": "un0",
            "info": {"rls_policy": "admin"},
        },
    )

    # Columns
    user_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "HAS_USER"},
    )
    group_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.group.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "HAS_GROUP"},
    )
    role_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.role.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "HAS_ROLE"},
    )

    # Relationships
    # user: Mapped[User] = relationship(back_populates="user_group_role")
    # group: Mapped[Group] = relationship(back_populates="user_group_role")
    # role: Mapped[Role] = relationship(back_populates="user_group_role")
