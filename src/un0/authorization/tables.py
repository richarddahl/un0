# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import textwrap
import datetime

from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
    Identity,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from sqlalchemy.dialects.postgresql import ENUM, ARRAY

from un0.authorization.enums import TenantType
from un0.database.enums import (
    SQLOperation,
)
# from un0.db.base import Base, BaseMixin, str_26, str_255  # type: ignore
# from un0.rltd.tables import TableType


class Tenant(Base, BaseMixin):
    """
    Represents organizations using the application

    Attributes:
        id (Mapped[str_26]): Primary key, foreign key to `un0.related_object.id`, with cascade delete.
        name (Mapped[str_255]): Unique name of the tenant.
        tenant_type (Mapped[TenantType]): Type of the tenant, defaults to `TenantType.INDIVIDUAL`.
        users (Mapped[list["User"]]): List of users that belong to the tenant.

    Methods:
        __str__() -> str: Returns the name of the tenant.
        __repr__() -> str: Returns a string representation of the tenant.
    """

    __tablename__ = "tenant"
    __table_args__ = (
        {
            "schema_name": "un0",
            "comment": "Application end-user tenants",
            "info": {"rls_policy": "superuser"},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        # server_default=func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_ID"},
    )
    name: Mapped[str_255] = mapped_column(unique=True, doc="Tenant name")
    tenant_type: Mapped[TenantType] = mapped_column(
        ENUM(TenantType, name="tenanttype", create_type=True, schema_name="un0"),
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


'''
class User(Base):
    """
    Application users.

    Attributes:
        id (str_26): Primary Key, foreign key to `un0.related_object.id`.
        email (str_255): Email address, used as login ID, unique.
        handle (str_255): User's displayed name and alternate login ID, unique.
        full_name (str_255): User's full name.
        tenant_id (Optional[str_26]): Foreign key to `un0.tenant.id`, nullable.
        default_group_id (Optional[str_26]): Foreign key to `un0.group.id`, nullable.
        is_superuser (bool): Superuser status, default is False.
        is_tenant_admin (bool): Tenant admin status, default is False.
        is_active (bool): Active status, default is True.
        is_deleted (bool): Deleted status, default is False.
        created_at (datetime.datetime): Time the record was created.
        owner_id (Optional[str_26]): Foreign key to `un0.user.id`.
        modified_at (datetime.datetime): Time the record was last modified.
        modified_by_id (Optional[str_26]): Foreign key to `un0.user.id`.
        deleted_at (Optional[datetime.datetime]): Time the record was deleted.
        deleted_by_id (Optional[str_26]): Foreign key to `un0.user.id`.

        tenant (Tenant): Tenant the user belongs to.
        default_group (Group): Default group for the user.
        modified_by (User): User that last modified the record.
        deleted_by (User): User that deleted the record.
        modified_users (list[User]): Users modified by the user.
        deleted_users (list[User]): Users deleted by the user.

    Methods:
        __str__(): Returns the email of the user.
        __repr__(): Returns a string representation of the user.
    """

    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint(
            textwrap.dedent(
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
        {
            "schema_name": "un0",
            "comment": "Application users",
            "info": {"audit_type": "history"},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        # server_default=func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_ID"},
    )
    email: Mapped[str_255] = mapped_column(
        unique=True, index=True, doc="Email address, used as login ID"
    )
    handle: Mapped[str_255] = mapped_column(
        unique=True, index=True, doc="User's displayed name and alternate login ID"
    )
    full_name: Mapped[str_255] = mapped_column(doc="User's full name")
    tenant_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey("un0.tenant.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
        info={"edge": "WORKS_FOR"},
    )
    default_group_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey("un0.group.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
        info={"edge": "HAS_DEFAULT_GROUP"},
    )
    is_superuser: Mapped[bool] = mapped_column(
        server_default=text("false"),
        index=True,
        doc="Superuser status",
        info={"column_security": "Secret"},
    )
    is_tenant_admin: Mapped[bool] = mapped_column(
        server_default=text("false"),
        index=True,
        doc="Tenant admin status",
        info={"column_security": "Secret"},
    )
    is_active: Mapped[bool] = mapped_column(
        server_default=text("true"),
        doc="Indicates if the record is active",
    )
    is_deleted: Mapped[bool] = mapped_column(
        server_default=text("false"),
        doc="Indicates if the record is deleted",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.current_timestamp(),
        doc="Time the record was created",
        info={"editable": False},
    )
    owner_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_OWNED_BY"},
    )
    modified_at: Mapped[datetime.datetime] = mapped_column(
        doc="Time the record was last modified",
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )
    modified_by_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "WAS_LAST_MODIFIED_BY", "editable": False},
    )
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        doc="Time the record was deleted",
        info={"editable": False},
    )
    deleted_by_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "WAS_DELETED_BY", "editable": False},
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

    def __str__(self) -> str:
        return self.email

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class TablePermission(Base):
    """
    Documents permissions for each table.

    Attributes:
        id (int): Primary key of the table, auto-incremented.
        table_type_id (TableType): Foreign key referencing the table type, with cascade delete.
        actions (list[SQLOperation]): List of permissible actions for the table.

    Methods:
        __str__: Returns a string representation of the TablePermission instance.
        __repr__: Returns a detailed string representation of the TablePermission instance.
    """

    __tablename__ = "tablepermission"
    __table_args__ = (
        UniqueConstraint(
            "table_type_id",
            "actions",
            name="uq_tabletype_actions",
        ),
        {
            "schema_name": "un0",
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
            "info": {"rls_policy": "superuser", "vertex": False},
        },
    )
    id: Mapped[int] = mapped_column(Identity(start=1, cycle=False), primary_key=True)
    table_type_id: Mapped[TableType] = mapped_column(
        ForeignKey("un0.table_type.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "HAS_TABLETYPE"},
    )
    actions: Mapped[list[SQLOperation]] = mapped_column(
        ARRAY(
            ENUM(
                SQLOperation,
                name="permission_name",
                create_type=True,
                schema_name="un0",
            )
        ),
        doc="Actions that are permissible",
    )

    def __str__(self) -> str:
        return f"{self.table_type} - {self.actions}"

    def __repr__(self) -> str:
        return f"<TablePermission {self.table_type} - {self.actions}>"


class Role(Base, BaseMixin):
    """
    Role Model

    Represents a role within the system, created by end user group admins. Roles enable the assignment of group permissions by functionality, department, etc., to users.

    Attributes:
        id (str_26): Primary key. Foreign key referencing `un0.related_object.id`. Indexed and cascades on delete.
        tenant_id (str_26): Foreign key referencing `un0.tenant.id`. Indicates the tenant the role belongs to. Indexed and cascades on delete.
        name (str_255): Name of the role.
        description (str): Description of the role.

    Methods:
        __str__(): Returns the name of the role.
        __repr__(): Returns a string representation of the role.
    """

    __tablename__ = "role"
    __table_args__ = (
        Index("ix_role_tenant_id_name", "tenant_id", "name"),
        UniqueConstraint("tenant_id", "name"),
        {
            "comment": """
                Roles, created by end user group admins, enable assignment of group_permissions
                by functionality, department, etc... to users.
            """,
            "schema_name": "un0",
            "info": {"rls_policy": "admin", "vertex": False},
        },
    )

    # Columns
    id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        # server_default=func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_ID"},
    )
    tenant_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.tenant.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant the role belongs to",
        info={"edge": "BELONGS_TO_TENANT"},
    )
    name: Mapped[str_255] = mapped_column(doc="Role name")
    description: Mapped[str] = mapped_column(doc="Role description")

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


class RoleTablePermission(Base):
    """
    RoleTablePermission is a SQLAlchemy model representing the association between roles and table permissions.

    Attributes:
        role_id (int): The ID of the role, which is a foreign key referencing the 'role' table.
        tablepermission_id (int): The ID of the table permission, which is a foreign key referencing the 'tablepermission' table.

    Methods:
        __str__: Returns a string representation of the RoleTablePermission instance.
        __repr__: Returns a detailed string representation of the RoleTablePermission instance.
    """

    __tablename__ = "role_tablepermission"
    __table_args__ = (
        {
            "comment": """
                Assigned by tenant_admin users to assign roles for groups to users based on organization requirements.
            """,
            "schema_name": "un0",
            "info": {"rls_policy": "none", "vertex": False},
        },
    )

    # Columns
    role_id: Mapped[int] = mapped_column(
        ForeignKey("un0.role.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="Role ID",
        info={"edge": "HAS_ROLE"},
    )
    tablepermission_id: Mapped[int] = mapped_column(
        ForeignKey("un0.tablepermission.id", ondelete="CASCADE"),
        index=True,
        primary_key=True,
        doc="Table Permission ID",
        info={"edge": "HAS_TABLEPERMISSION"},
    )

    def __str__(self) -> str:
        return f"{self.role_id} - {self.tablepermission_id}"

    def __repr__(self) -> str:
        return f"<RoleTablePermission {self.role_id} - {self.tablepermission_id}>"


class Group(Base, BaseMixin):
    """
    Group model representing application end-user groups.

    Attributes:
        id (Mapped[str_26]): Primary key of the group, linked to the related object with a cascading delete.
        tenant_id (Mapped[str_26]): Foreign key linking the group to a tenant, with a cascading delete.
        name (Mapped[str_255]): Name of the group.
        users_default_group (Mapped[list["User"]]): List of users that have this group as their default group.

    Methods:
        __str__() -> str: Returns the name of the group.
        __repr__() -> str: Returns a string representation of the group.
    """

    __tablename__ = "group"
    __table_args__ = (
        Index("ix_group_tenant_id_name", "tenant_id", "name"),
        UniqueConstraint("tenant_id", "name"),
        {
            "comment": "Application end-user groups",
            "schema_name": "un0",
            "info": {"rls_policy": "admin"},
        },
    )

    # Columns

    id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        # server_default=func.un0.insert_related_object("un0", "user"),
        doc="Primary Key",
        info={"edge": "HAS_ID"},
    )
    tenant_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.tenant.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "BELONGS_TO_TENANT"},
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


class UserGroupRole(Base):
    """
    Represents the association between users, groups, and roles within an organization.

    This table is used to assign roles to users for specific groups based on organizational requirements.
    The assignments are managed by tenant_admin users.

    Attributes:
        user_id (Mapped[str_26]): Foreign key referencing the user's ID.
            - Indexed, not nullable, primary key.
            - On delete cascade.
            - Info: {"edge": "HAS_USER"}

        group_id (Mapped[str_26]): Foreign key referencing the group's ID.
            - Indexed, not nullable, primary key.
            - On delete cascade.
            - Info: {"edge": "HAS_GROUP"}

        role_id (Mapped[str_26]): Foreign key referencing the role's ID.
            - Indexed, not nullable, primary key.
            - On delete cascade.
            - Info: {"edge": "HAS_ROLE"}

    Table Info:
        - Comment: Assigned by tenant_admin users to assign roles for groups to users based on organization requirements.
        - Schema: "un0"
        - Info: {"rls_policy": "admin", "vertex": False}
    """

    __tablename__ = "user_group_role"
    __table_args__ = (
        {
            "comment": """
                Assigned by tenant_admin users to assign roles for groups to users based on organization requirements.
            """,
            "schema_name": "un0",
            "info": {"rls_policy": "admin", "vertex": False},
        },
    )

    # Columns
    user_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        primary_key=True,
        info={"edge": "HAS_USER"},
    )
    group_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.group.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        primary_key=True,
        info={"edge": "HAS_GROUP"},
    )
    role_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.role.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        primary_key=True,
        info={"edge": "HAS_ROLE"},
    )

'''
