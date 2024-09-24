# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import pytest
import json

import sqlalchemy as sa
from sqlalchemy.sql import select

from un0.auth.models import Customer, User, Role, Group, UserGroupRole
from un0.auth.enums import CustomerType
from un0.config import settings


@pytest.mark.asyncio
async def test_admin_user(setup_database, valid_user):
    """Tests that the admin user, created in create_db.create_db is created correctlty."""
    admin_user = valid_user
    assert admin_user is not None
    assert admin_user.email == "app_admin@notorm.tech"
    assert admin_user.handle == "admin"
    assert admin_user.full_name == "App Admin"
    assert admin_user.is_superuser is True
    assert admin_user.is_customer_admin is False
    assert admin_user.is_active is True
    assert admin_user.is_deleted is False
    assert admin_user.created_at is not None
    assert admin_user.modified_at is not None
    assert admin_user.deleted_at is None


@pytest.mark.asyncio
async def test_admin_user_graph(setup_database, async_session, valid_user):
    """Tests that the graph vertext for the admin user was created correctlty."""
    admin_user = valid_user
    async with async_session() as session:
        await session.execute(sa.text(f"SET ROLE {settings.DB_NAME}_admin"))
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
        assert properties["email"] == "app_admin@notorm.tech"
        assert properties["handle"] == "admin"
        assert properties["full_name"] == "App Admin"
        assert properties["is_superuser"] == "true"
        assert properties["is_customer_admin"] == "false"
        assert properties["is_active"] == "true"
        assert properties["is_deleted"] == "false"
        assert properties["created_at"] is not None
        assert properties["modified_at"] is not None
        with pytest.raises(KeyError):
            properties["deleted_at"]
