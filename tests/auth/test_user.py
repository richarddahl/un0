# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import pytest
import json

import sqlalchemy as sa

from un0.auth.models import User

from tests.conftest import encode_token
from un0.config import settings


@pytest.fixture
async def admin_user(async_session):
    token = encode_token()
    async with async_session() as session:
        token_result = await session.execute(
            sa.text(f"SELECT * FROM un0.verify_jwt_and_set_vars('{token}'::TEXT);")
        )
        assert token_result.scalars().first() is True

        result = await session.execute(
            sa.text("SELECT * FROM un0.list_session_variables();")
        )
        session_variables = result.scalars().first()
        assert session_variables.get("user_id") != ""
        assert session_variables.get("is_superuser") == "true"
        assert session_variables.get("is_customer_admin") == "false"
        assert session_variables.get("customer_id") == ""

        q = sa.sql.select(User).where(User.email == settings.SUPERUSER_EMAIL)
        result = await session.execute(q)
        return result.scalars().first()


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
        assert properties["email"] == str(admin_user.email)
        assert properties["handle"] == str(admin_user.handle)
        assert properties["full_name"] == str(admin_user.full_name)
        assert properties["is_superuser"] == str(admin_user.is_superuser).lower()
        assert (
            properties["is_customer_admin"] == str(admin_user.is_customer_admin).lower()
        )
        assert properties["is_active"] == str(admin_user.is_active).lower()
        assert properties["is_deleted"] == str(admin_user.is_deleted).lower()
        assert properties["created_at"] == str(admin_user.created_at).split("+")[0]
        assert properties["modified_at"] == str(admin_user.modified_at).split("+")[0]
        with pytest.raises(KeyError):
            properties["deleted_at"]
