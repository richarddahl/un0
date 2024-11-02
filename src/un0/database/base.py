# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import datetime

from enum import Enum
from typing import AsyncIterator

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, registry
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
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

from un0.database.pg_types import str_26, str_64, str_128, str_255, decimal
from un0.config import settings


# configures the naming convention for the database implicit constraints and indexes
POSTGRES_INDEXES_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}

# Creates the metadata object, used to define the database tables
meta_data = MetaData(
    naming_convention=POSTGRES_INDEXES_NAMING_CONVENTION,
    schema=settings.DB_NAME,
)


# Create the database engine
engine = create_async_engine(settings.DB_URL)

# Create a sessionmaker factory
async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=True,
    class_=AsyncSession,
)


# Dependency to provide a session
async def get_db() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for SQLAlchemy models with asynchronous attributes and custom type annotations.

    Attributes:
        registry (sqlalchemy.orm.registry): A registry object that maps Python types to SQLAlchemy column types.
        metadata (sqlalchemy.MetaData): Metadata object for the database schema_name.

    Type Annotations:
        int: BIGINT
        datetime.datetime: TIMESTAMP(timezone=True)
        datetime.date: DATE
        datetime.time: TIME
        str: VARCHAR
        Enum: ENUM
        bool: BOOLEAN
        list: ARRAY
        str_26: VARCHAR(26)
        str_64: VARCHAR(64)
        str_128: VARCHAR(128)
        str_255: VARCHAR(255)
        decimal: NUMERIC
    """

    registry = registry(
        type_annotation_map=(
            {
                int: BIGINT,
                datetime.datetime: TIMESTAMP(timezone=True),
                datetime.date: DATE,
                datetime.time: TIME,
                str: VARCHAR,
                Enum: ENUM,
                bool: BOOLEAN,
                list: ARRAY,
                str_26: VARCHAR(26),
                str_64: VARCHAR(64),
                str_128: VARCHAR(128),
                str_255: VARCHAR(255),
                decimal: NUMERIC,
            }
        )
    )
    metadata = meta_data
