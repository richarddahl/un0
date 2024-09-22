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

from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
import sqlalchemy as sa
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
engine = sa.create_engine(settings.DB_URL)


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
meta_data = sa.MetaData(
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


class TableType(Base):
    """Table Types identify the tables in the database, similar to contenttypes in Django"""

    __tablename__ = "table_type"
    __table_args__ = (
        sa.UniqueConstraint("schema", "name", name="uq_table_type_schema_name"),
        {
            "schema": "un0",
            "comment": "Table Types identify the tables in the database, similar to contenttypes in Django",
            "info": {"rls_policy": "superuser"},
        },
    )

    id: Mapped[int] = mapped_column(
        sa.Identity(start=1, cycle=False),
        primary_key=True,
        index=True,
        doc="Primary Key",
    )
    schema: Mapped[str_255] = mapped_column(doc="Schema of the table")
    name: Mapped[str_255] = mapped_column(doc="Name of the table")

    # Relationships
    """
    # related_object: Mapped["RelatedObject"] = relationship(
    #    back_populates="table_type",
    #    foreign_keys="RelatedObject.table_type_id",
    #    doc="Related Object of the table",
    # )
    workflows: Mapped[list["Workflow"]] = relationship(
        back_populates="applicable_table_type",
        foreign_keys="Workflow.applicable_table_type_id",
        doc="Workflows applicable to the table",
    )
    object_functions: Mapped[list["ObjectFunction"]] = relationship(
        back_populates="table_type",
        doc="Object Functions of the table",
    )
    table_permissions: Mapped[list["TablePermission"]] = relationship(
        back_populates="table_type",
        doc="Permissions of the table",
    )
    fields: Mapped[list["Field"]] = relationship(
        back_populates="table_type",
        doc="Fields of the table",
    )
    source_filter_keys: Mapped[list["FilterKey"]] = relationship(
        back_populates="source",
        foreign_keys="FilterKey.source_id",
        doc="Source Filter Keys of the table",
    )
    destination_filter_keys: Mapped[list["FilterKey"]] = relationship(
        back_populates="destination",
        foreign_keys="FilterKey.destination_id",
        doc="Destination Filter Keys of the table",
    )
    """


class RelatedObject(Base):
    """Related Objects are used for the pk of all objects in the database,
    allowing for a single point of reference for queries, workflows, and reports
    """

    __tablename__ = "related_object"
    __table_args__ = {
        "schema": "un0",
        "comment": textwrap.dedent(
            """
            Related Objects are used for the pk of all objects in the database,
            allowing for a single point of reference for queries, workflows, and reports
            """
        ),
    }

    # Columns
    id: Mapped[str_26] = mapped_column(
        primary_key=True,
        nullable=False,
        index=True,
        server_default=sa.func.un0.generate_ulid(),
        doc="Primary Key",
    )

    # table_type_id: Mapped[int] = mapped_column(
    #    sa.ForeignKey("un0.table_type.id", ondelete="CASCADE"),
    #    index=True,
    #    nullable=False,
    #    info={"graph_properties": False},
    # )

    # Relationships
    # table_type: Mapped["TableType"] = relationship(
    #    back_populates="related_object",
    #    foreign_keys="RelatedObject.table_type_id",
    # )
    # workflow_record: Mapped[list["WorkflowRecord"]] = relationship(
    #    back_populates="record",
    #    foreign_keys="WorkflowRecord.record_id",
    # )
    # workflow_event: Mapped[list["WorkflowEvent"]] = relationship(
    #    back_populates="workflow_object",
    #    foreign_keys="WorkflowEvent.object_id",
    # )
    # message_object: Mapped[list["MessageObject"]] = relationship(
    #    back_populates="object",
    #    foreign_keys="MessageObject.object_id",
    # )
    # filter_key: Mapped[list["FilterKey"]] = relationship(
    #    back_populates="related_object",
    #    foreign_keys="FilterKey.related_object_id",
    # )
    # filter_value: Mapped["FilterValue"] = relationship(
    #    back_populates="related_object",
    #    foreign_keys="FilterValue.related_object_id",
    # )
    # filter_object_values: Mapped[list["FilterValue"]] = relationship(
    #    back_populates="object_value",
    #    foreign_keys="FilterValue.object_value_id",
    #    doc="Filter Values Object Values",
    # )


class BaseMixin:
    # Columns
    id: Mapped[str_26] = mapped_column(
        primary_key=True,
        index=True,
        server_default=sa.func.un0.generate_ulid(),
        doc="Primary Key",
    )
    related_object_id: Mapped[Optional[str_26]] = mapped_column(
        sa.ForeignKey("un0.related_object.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=True,
        doc="Related Object of the record",
        info={"edge": "HAS_RELATED_OBJECT"},
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
    modified_at: Mapped[datetime.datetime] = mapped_column(
        doc="Time the record was last modified",
        server_default=sa.func.current_timestamp(),
    )
    deleted_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        doc="Time the record was deleted"
    )
    import_id: Mapped[Optional[int]] = mapped_column(
        doc="Primary Key of the original system of the record"
    )
    import_key: Mapped[Optional[str]] = mapped_column(
        doc="Unique identifier of the original system of the record"
    )

    # When importing from other systems we need to ensure that the import_id
    # and import_key are unique for the table_type
    sa.UniqueConstraint(
        "table_type_id", "import_id", name="uq_audit_meta_table_type_import_id"
    )
    # the import_id is the primary key of the source system and the import_key
    # is a unique identifier that may exist in the source system
    sa.UniqueConstraint(
        "table_type_id", "import_key", name="uq_audit_meta_table_type_import_key"
    )

    # Relationships
    # @declared_attr
    # def related_object(cls) -> Mapped["RelatedObject"]:
    #    return relationship(
    #        back_populates="related_object",
    #        doc="Related Object of the record",
    #    )


class RBACMixin:
    # Columns
    customer_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.customer.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "HAS_CUSTOMER"},
    )
    owner_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "WAS_CREATED_BY"},
    )
    modified_by_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
        info={"edge": "WAS_LAST_MODIFIED_BY"},
    )
    deleted_by_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.user.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
        info={"edge": "WAS_DELETED_BY"},
    )
    group_id: Mapped[str_26] = mapped_column(
        sa.ForeignKey("un0.group.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
        info={"edge": "IS_ACCESSIBLE_BY"},
    )

    # Relationships
    """
    @declared_attr
    def customer(cls) -> Mapped["Customer"]:
        return relationship(
            foreign_keys=[cls.customer_id],
            back_populates="related_object",
            doc="Customer",
        )

    @declared_attr
    def owner(cls) -> Mapped["User"]:
        return relationship(
            foreign_keys=[cls.owner_id],
            back_populates="owned",
            doc="User that owns the record",
        )

    @declared_attr
    def modified_by(cls) -> Mapped["User"]:
        return relationship(
            back_populates="modified",
            foreign_keys=[cls.modified_by_id],
            doc="User that last modified the record",
        )

    @declared_attr
    def deleted_by(cls) -> Mapped["User"]:
        return relationship(
            back_populates="deleted",
            foreign_keys=[cls.deleted_by_id],
            doc="User that deleted the record",
        )

    @declared_attr
    def group(cls) -> Mapped["Group"]:
        return relationship(
            back_populates="related_object",
            foreign_keys=[cls.group_id],
            doc="Group of the record",
        )
    """
