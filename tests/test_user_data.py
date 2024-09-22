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
async def test_admin_user(setup_database, async_session):
    """Tests that the admin user, created in create_db.create_db is created correctlty."""
    async with async_session() as session:
        await session.execute(sa.text(f"SET ROLE {settings.DB_NAME}_reader"))
        q = select(User).where(User.email == "admin@notorm.tech")
        result = await session.execute(q)
        admin_user = result.scalars().first()

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
        json_data = json.loads(admin_user_vertex.first()[0])
        assert json_data["email"] == "admin@notorm.tech"

    assert admin_user is not None
    assert admin_user.email == "admin@notorm.tech"
    assert admin_user.handle == "admin_user"
    assert admin_user.full_name == "Admin User"
    assert admin_user.is_superuser is True
    assert admin_user.is_active is True
    assert admin_user.is_deleted is False


@pytest.mark.asyncio
async def test_create_customer(setup_database, async_session):
    async with async_session() as session:
        await session.execute(sa.text(f"SET ROLE {settings.DB_NAME}_reader"))
        q = select(User).where(User.email == "admin@notorm.tech")
        result = await session.execute(q)
        admin_user = result.scalars().first()

        await session.execute(sa.text(f"SET ROLE {settings.DB_NAME}_writer"))
        await session.execute(sa.text(f"SET SESSION un0.app_user = '{admin_user.id}'"))

        acme = Customer(name="Acme Inc.", customer_type=CustomerType.ENTERPRISE)
        nacme = Customer(name="NAcme Inc.", customer_type=CustomerType.CORPORATE)
        coyote = Customer(
            name="Wiley Coyote", customer_type=CustomerType.SMALL_BUSINESS
        )
        bird = Customer(name="Road Runner", customer_type=CustomerType.INDIVIDUAL)
        session.add_all([acme, nacme, coyote, bird])

        customer_count = await session.execute(
            select(sa.func.count()).select_from(Customer)
        )
        assert customer_count.scalar() == 4
        group_count = await session.execute(select(sa.func.count()).select_from(Group))
        assert group_count.scalar() == 4
    '''
    # Create roles
    acme_admin_role = Role(
        name="Admin", description="Administrator role", customer_id=acme.id
    )
    acme_user_role = Role(
        name="User", description="Regular user role", customer_id=acme.id
    )
    nacme_admin_role = Role(
        name="Admin", description="Administrator role", customer_id=nacme.id
    )
    nacme_user_role = Role(
        name="User", description="Regular user role", customer_id=nacme.id
    )
    coyote_admin_role = Role(
        name="Admin", description="Administrator role", customer_id=coyote.id
    )
    coyote_user_role = Role(
        name="User", description="Regular user role", customer_id=coyote.id
    )
    bird_admin_role = Role(
        name="Admin", description="Administrator role", customer_id=bird.id
    )
    bird_user_role = Role(
        name="User", description="Regular user role", customer_id=bird.id
    )
    session.add_all(
        [
            acme_admin_role,
            acme_user_role,
            nacme_admin_role,
            nacme_user_role,
            coyote_admin_role,
            coyote_user_role,
            bird_admin_role,
            bird_user_role,
        ]
    )
    session.commit()
    # Create groups
    group_sales = Group(name="Sales", customer_id=acme.id)
    group_support = Group(name="Support", customer_id=acme.id)
    session.add_all([group_sales, group_support])
    session.commit()
    group_sales = Group(name="Sales", customer_id=nacme.id)
    group_support = Group(name="Support", customer_id=nacme.id)
    session.add_all([group_sales, group_support])
    session.commit()
    group_sales = Group(name="Sales", customer_id=coyote.id)
    group_support = Group(name="Support", customer_id=coyote.id)
    session.add_all([group_sales, group_support])
    session.commit()
    assert session.query(Group).count() == 10
    """
    # Create users
    user_john = User(
        email="john@example.com",
        handle="john",
        full_name="John Doe",
        customer_id="1",
        default_group_id=group_sales.id,
    )
    user_jane = User(
        email="jane@example.com",
        handle="jane",
        full_name="Jane Doe",
        customer_id="1",
        default_group_id=group_support.id,
    )
    session.add_all([user_john, user_jane])
    session.commit()

    # Assign roles to users in groups
    user_group_role_john = UserGroupRole(
        user_id=user_john.id, group_id=group_sales.id, role_id=role_admin.id
    )
    user_group_role_jane = UserGroupRole(
        user_id=user_jane.id, group_id=group_support.id, role_id=role_user.id
    )
    session.add_all([user_group_role_john, user_group_role_jane])
    session.commit()
    """

    # Verify data
    assert session.query(Role).count() == 8
    # assert session.query(User).count() == 8
    # assert session.query(Group).count() == 2
    # assert session.query(UserGroupRole).count() == 2

    session.close()
    '''
