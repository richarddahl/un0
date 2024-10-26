# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import contextlib

from typing import Optional

from enum import Enum
from decimal import Decimal
from typing import Annotated, AsyncIterator

from asyncio import current_task

from sqlalchemy import create_engine, MetaData, text, func, ForeignKey
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.dialects.postgresql import (
    BIGINT,
    TIMESTAMP,
    DATE,
    TIME,
    VARCHAR,
    BOOLEAN,
    ENUM,
    NUMERIC,
    ARRAY,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    relationship,
    registry,
    declared_attr,
    mapped_column,
)
from un0.config import settings as sttngs


# configures the naming convention for the database implicit constraints and indexes
POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "%(column_0_label)s_idx",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}

# Creates the metadata object, used to define the database tables
meta_data = MetaData(
    naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION,
    schema=sttngs.DB_NAME,
)

str_26 = Annotated[VARCHAR, 26]
str_128 = Annotated[VARCHAR, 128]
str_255 = Annotated[VARCHAR, 255]
decimal = Annotated[Decimal, 19]


class Base(AsyncAttrs, DeclarativeBase):
    registry = registry(
        type_annotation_map={
            int: BIGINT,
            datetime.datetime: TIMESTAMP(timezone=True),
            datetime.date: DATE,
            datetime.time: TIME,
            str: VARCHAR,
            Enum: ENUM,
            bool: BOOLEAN,
            list: ARRAY,
            str_26: VARCHAR(26),
            str_128: VARCHAR(128),
            str_255: VARCHAR(255),
            decimal: NUMERIC,
        }
    )
    metadata = meta_data


class BaseMixin:
    # Columns
    is_active: Mapped[bool] = mapped_column(
        server_default=text("true"),
        doc="Indicates if the record is active",
    )
    is_deleted: Mapped[bool] = mapped_column(
        server_default=text("false"),
        doc="Indicates if the record has been deleted",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.current_timestamp(),
        doc="Time the record was created",
        info={"editable": False},
    )
    owner_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_OWNED_BY"},
    )
    modified_at: Mapped[datetime.datetime] = mapped_column(
        doc="Time the record was last modified",
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
        info={"editable": False},
    )
    modified_by_id: Mapped[str_26] = mapped_column(
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
    import_id: Mapped[Optional[int]] = mapped_column(
        doc="Primary Key of the original system of the record"
    )

    import_key: Mapped[Optional[str]] = mapped_column(
        doc="Unique identifier of the original system of the record"
    )

    # Relationships
    # @declared_attr
    # @classmethod
    # def relatedobject(cls) -> Mapped["RelatedObject"]:
    #    return relationship(
    #        back_populates="relatedobject",
    #        doc="Related Object of the record",
    #    )

    # @declared_attr
    # @classmethod
    # def modified_by(cls) -> Mapped["User"]:
    #    return relationship(
    #        back_populates="modified_by",
    #        foreign_keys=[cls.modified_by_id],
    #        doc="User that last modified the record",
    #    )

    # @declared_attr
    # @classmethod
    # def deleted_by(cls) -> Mapped["User"]:
    #    return relationship(
    #        back_populates="deleted_by",
    #        foreign_keys=[cls.deleted_by_id],
    #        doc="User that deleted the record",
    #    )


class RBACMixin:
    # Columns
    @declared_attr
    @classmethod
    def tenant_id(cls) -> Mapped[str_26]:
        return mapped_column(
            ForeignKey("un0.tenant.id", ondelete="CASCADE"),
            index=True,
            info={"edge": "HAS_TENANT"},
        )

    @declared_attr
    @classmethod
    def group_id(cls) -> Mapped[str_26]:
        return mapped_column(
            ForeignKey("un0.group.id", ondelete="CASCADE"),
            index=True,
            info={"edge": "IS_ACCESSIBLE_BY"},
        )

    # Relationships
    # @declared_attr
    # def tenant(cls) -> Mapped["Tenant"]:
    #    return relationship(
    #        foreign_keys=[cls.tenant_id],
    #        back_populates="tenant",
    #        doc="Tenant",
    #    )

    # @declared_attr
    # def group(cls) -> Mapped["Group"]:
    #    return relationship(
    #        back_populates="relatedobject",
    #        foreign_keys=[cls.group_id],
    #        doc="Group of the record",
    #    )
