# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import textwrap
import contextlib

from typing import Optional

from enum import Enum
from decimal import Decimal
from typing import Annotated, AsyncIterator

from sqlalchemy import create_engine, MetaData, text, func, ForeignKey
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncConnection,
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

from un0.config import settings


# Creates the async engine and sets the echo to true if DEBUG is true
async_engine = create_async_engine(settings.DB_URL)
engine = create_engine(settings.DB_URL)


class DatabaseSessionManager:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker | None = None

    def init(self, host: str) -> None:
        self._engine = create_async_engine(host)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self) -> None:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager()


async def get_db() -> AsyncIterator[AsyncSession]:
    async with sessionmanager.session() as session:
        yield session


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
    schema=settings.DB_NAME,
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
    is_active: Mapped[bool] = mapped_column(server_default=text("true"), doc="Active")
    is_deleted: Mapped[bool] = mapped_column(
        server_default=text("false"), doc="Deleted"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=func.current_timestamp(),
        doc="Time the record was created",
    )
    owner_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "IS_OWNED_BY"},
    )
    modified_at: Mapped[datetime.datetime] = mapped_column(
        doc="Time the record was last modified",
        server_default=func.current_timestamp(),
    )
    modified_by_id: Mapped[str_26] = mapped_column(
        ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "WAS_LAST_MODIFIED_BY"},
    )
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        doc="Time the record was deleted"
    )
    deleted_by_id: Mapped[Optional[str_26]] = mapped_column(
        ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        info={"edge": "WAS_DELETED_BY"},
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
