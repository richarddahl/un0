# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import datetime
import pytest
import json
import pytz

import sqlalchemy as sa

from un0.config import settings
from un0.auth.models import Customer, User
from un0.auth.enums import CustomerType
from tests.conftest import (
    SUPERUSER_SESSION_CONFIGURATION_STATEMENTS,
    SET_ROLE_ADMIN_STATEMENT,
    SET_ROLE_READER_STATEMENT,
    SET_ROLE_WRITER_STATEMENT,
)


@pytest.mark.asyncio
async def test_admin_user(admin_user):
    """Tests that the admin user, created in create_db.create_db is created correctly."""
    admin_user = await admin_user
    assert admin_user is not None
    assert admin_user.email == settings.SUPERUSER_EMAIL
    assert admin_user.handle == settings.SUPERUSER_HANDLE
    assert admin_user.full_name == settings.SUPERUSER_FULL_NAME
    assert admin_user.is_superuser is True
    assert admin_user.is_customer_admin is False
    assert admin_user.is_active is True
    assert admin_user.is_deleted is False
    assert admin_user.created_at is not None
    assert admin_user.modified_at is not None
    assert admin_user.deleted_at is None


@pytest.mark.asyncio
async def test_admin_user_graph(async_session, admin_user):
    """Tests that the graph vertext for the admin user was created correctly."""
    admin_user = await admin_user
    async with async_session() as session:
        await session.execute(sa.text(SET_ROLE_ADMIN_STATEMENT))
        stmt = sa.text(
            f"""
            SELECT * FROM cypher('graph', $$
            MATCH (u:User)
            WHERE (u.id = '{admin_user.id}')
            RETURN properties(u)
            $$) as (type agtype);
            """
        )
        admin_user_vertex = await session.execute(stmt)
        properties = json.loads(admin_user_vertex.first()[0])
        assert properties["email"] == str(admin_user.email)
        assert properties["handle"] == str(admin_user.handle)
        assert properties["full_name"] == str(admin_user.full_name)
        assert properties["is_superuser"] == str(admin_user.is_superuser).lower()
        assert (
            properties["is_customer_admin"] == str(admin_user.is_customer_admin).lower()
        )
        assert properties["is_active"] == str(admin_user.is_active).lower()
        assert properties["is_deleted"] == str(admin_user.is_deleted).lower()
        _graph_created_at = datetime.datetime.strptime(
            properties["created_at"], "%Y-%m-%d %H:%M:%S.%f"
        ).replace(tzinfo=pytz.UTC)
        assert _graph_created_at == admin_user.created_at.replace(tzinfo=pytz.UTC)

        _graph_modified_at = datetime.datetime.strptime(
            properties["modified_at"], "%Y-%m-%d %H:%M:%S.%f"
        ).replace(tzinfo=pytz.UTC)
        assert _graph_modified_at == admin_user.modified_at.replace(tzinfo=pytz.UTC)
        with pytest.raises(KeyError):
            properties["deleted_at"]


@pytest.mark.asyncio
async def test_reader_role_cannot_create_object(async_session):
    """Tests that an object cannot be created by the reader role."""
    async with async_session() as session:
        await session.execute(sa.text(SUPERUSER_SESSION_CONFIGURATION_STATEMENTS))
        acme = Customer(name="Acme Inc.", customer_type=CustomerType.ENTERPRISE)
        session.add(acme)
        with pytest.raises(sa.exc.ProgrammingError):
            await session.commit()


@pytest.mark.asyncio
async def test_super_user_create_user(async_session):
    """Tests that a user can be created by a superuser ."""
    async with async_session() as session:
        await session.execute(sa.text(SUPERUSER_SESSION_CONFIGURATION_STATEMENTS))
        acme = Customer(name="Acme Inc.", customer_type=CustomerType.ENTERPRISE)
        acme_admin = User(
            email="admin@acme.com",
            handle="acme admin",
            full_name="ACME Admin",
            is_superuser=False,
            is_customer_admin=True,
            customer_id=acme.id,
        )
        session.add(acme, acme_admin)
        await session.execute(sa.text(SET_ROLE_WRITER_STATEMENT))
        result = await session.commit()
        assert result is None


@pytest.mark.asyncio
async def test_super_user_select_object_with_roles(async_session):
    """Tests that a user can be read by a superuser with each of the db ROLEs."""
    async with async_session() as session:
        await session.execute(sa.text(SUPERUSER_SESSION_CONFIGURATION_STATEMENTS))
        await session.execute(sa.text(SET_ROLE_ADMIN_STATEMENT))
        stmt = sa.select(Customer).filter_by(name="Acme Inc.")
        result = await session.scalars(stmt)
        acme = result.first()
        assert acme is not None

        await session.execute(sa.text(SET_ROLE_WRITER_STATEMENT))
        stmt = sa.select(Customer).filter_by(name="Acme Inc.")
        result = await session.scalars(stmt)
        acme = result.first()
        assert acme is not None

        await session.execute(sa.text(SET_ROLE_READER_STATEMENT))
        stmt = sa.select(Customer).filter_by(name="Acme Inc.")
        result = await session.scalars(stmt)
        acme = result.first()
        assert acme is not None


'''
@pytest.mark.asyncio
async def test_customer_admin_user_create_user(async_session):
    """Tests that a user can be created by a customer admin, but only with the same customer_id."""
    async with async_session() as session:
        await session.execute(sa.text(SUPERUSER_SESSION_CONFIGURATION_STATEMENTS))
        acme = Customer.(name="Acme Inc.")

        nacme = Customer(name="Nacme Inc.", customer_type=CustomerType.CORPORATE)
        acme_admin = User(
            email="admin@acme.com",
            handle="acme admin",
            full_name="ACME Admin",
            is_superuser=False,
            is_customer_admin=True,
            customer_id=acme.id,
        )
        session.add(acme, acme_admin)
        await session.execute(sa.text(SET_ROLE_WRITER_STATEMENT))
        result = await session.commit()
        assert result is None

'''
