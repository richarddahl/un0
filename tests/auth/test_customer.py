# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT
import pytest
import json

import sqlalchemy as sa
from sqlalchemy.sql import select

from un0.auth.models import Customer, Group, User
from un0.auth.enums import CustomerType
from un0.config import settings


'''
@pytest.mark.asyncio
async def test_create_groups_on_customer_creation(async_session, admin_user):
    admin_user = await admin_user
    async with async_session() as session:
        await session.execute(sa.text(f"SET ROLE {settings.DB_NAME}_writer"))

        acme = Customer(name="Acme Inc.", customer_type=CustomerType.ENTERPRISE)
        nacme = Customer(name="NAcme Inc.", customer_type=CustomerType.CORPORATE)
        coyote = Customer(
            name="Wiley Coyote", customer_type=CustomerType.SMALL_BUSINESS
        )
        bird = Customer(name="Road Runner", customer_type=CustomerType.INDIVIDUAL)
        customers = [acme, nacme, coyote, bird]
        session.add_all(customers)
        await session.commit()

        customer_count = await session.execute(
            select(sa.func.count()).select_from(Customer)
        )
        assert customer_count.scalar() == 4
        group_count = await session.execute(select(sa.func.count()).select_from(Group))
        assert group_count.scalar() == 4


@pytest.mark.asyncio
async def test_customer_graphs(async_session, admin_user):
    admin_user = await admin_user
    async with async_session() as session:
        await session.execute(sa.text(f"SET ROLE {settings.DB_NAME}_admin"))
        stmt = sa.text(
            """
            SELECT * FROM cypher('graph', $$
            MATCH (c:Customer)
            RETURN properties(c)
            $$) as (type agtype);
            """
        )
        customer_vertex = await session.execute(stmt)
        for props in customer_vertex.fetchall():
            properties = json.loads(props[0])
            assert properties["created_at"] is not None
            assert properties["modified_at"] is not None
            with pytest.raises(KeyError):
                properties["deleted_at"]
    # assert properties["name"] == "Acme Inc."
    # assert properties["customer_type"] == "ENTERPRISE"
    # assert properties["created_at"] is not None
    # assert properties["modified_at"] is not None
    # with pytest.raises(KeyError):
    #     properties["deleted_at"]


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
