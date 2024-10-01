# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
This module contains the global fixtures for the tests in all test modules.
Each test module has its own conftest.py file that containts the fixtures for that module.
"""
import os

import pytest

from sqlalchemy import create_engine, func, select, delete
from sqlalchemy.orm import sessionmaker

from un0.auth.models import Tenant, Group, User
from un0.auth.enums import TenantType
from un0.config import settings as sttngs
from un0.cmd import create_db, drop_db


#############################
# FUNCTIONS CALLED BY TESTS #
#############################


def get_mock_user_vars(
    email: str = sttngs.SUPERUSER_EMAIL,
    is_superuser: str = "true",
    is_tenant_admin: str = "false",
    tenant_id: str = "",
):
    return (id, email, is_superuser, is_tenant_admin, tenant_id)


############
# FIXTURES #
############


@pytest.fixture(scope="session")
def tenant_dict(session, user_rluser_vars):
    tenant_list = [
        ["Acme Inc.", TenantType.ENTERPRISE],
        ["Nacme Corp", TenantType.CORPORATE],
        ["Coyote LLP", TenantType.SMALL_BUSINESS],
        ["Birdy", TenantType.INDIVIDUAL],
    ]
    tenants = [
        Tenant(name=name, tenant_type=tenant_type) for name, tenant_type in tenant_list
    ]
    with session.begin():
        session.execute(func.un0.test_set_mock_user_vars(*user_rluser_vars))
        session.execute(func.un0.set_role("writer"))
        session.add_all(tenants)
        result = session.execute(select(Tenant))
        db_tenants = result.scalars().all()
    tenant_dict = {
        t.name: {"id": t.id, "tenant_type": t.tenant_type} for t in db_tenants
    }
    yield tenant_dict
    session.execute(func.un0.test_set_mock_user_vars(*user_rluser_vars))
    session.execute(func.un0.set_role("writer"))
    session.execute(delete(Tenant).where(Tenant.id != ""))


@pytest.fixture(scope="session")
def group_dict(session, user_rluser_vars):
    with session.begin():
        session.execute(func.un0.test_set_mock_user_vars(*user_rluser_vars))
        result = session.execute(select(Group))
        db_groups = result.scalars().all()
        group_dict = {g.name: {"id": g.id} for g in db_groups}

    yield group_dict
    session.execute(func.un0.test_set_mock_user_vars(*user_rluser_vars))
    session.execute(func.un0.set_role("writer"))
    session.execute(delete(Group).where(Group.id != ""))


@pytest.fixture(scope="session")
def user_dict(session, user_rluser_vars, tenant_dict, group_dict):
    users = []
    for tenant_name, tenant_value in tenant_dict.items():
        tenant_name_lower = tenant_name.split(" ")[0].lower()
        tenant_id = tenant_value.get("id")
        default_group_id = group_dict.get(tenant_name).get("id")
        users.append(
            User(
                email=f"{'admin'}@{tenant_name_lower}.com",
                handle=f"{tenant_name_lower}_admin",
                full_name=f"{tenant_name} Admin",
                is_tenant_admin=True,
                tenant_id=tenant_id,
                default_group_id=default_group_id,
            )
        )
        if tenant_value.get("tenant_type") == TenantType.ENTERPRISE:
            rng = range(1, 10)
        elif tenant_value.get("tenant_type") == TenantType.CORPORATE:
            rng = range(1, 5)
        elif tenant_value.get("tenant_type") == TenantType.SMALL_BUSINESS:
            rng = range(1, 3)
        else:
            rng = range(1, 1)
        for u in rng:
            users.append(
                User(
                    email=f"{'user'}{u}@{tenant_name_lower}.com",
                    handle=f"{tenant_name_lower}_user{u}",
                    full_name=f"{tenant_name} User{u}",
                    tenant_id=tenant_id,
                    default_group_id=default_group_id,
                )
            )
    with session.begin():
        session.execute(func.un0.test_set_mock_user_vars(*user_rluser_vars))
        session.execute(func.un0.set_role("writer"))
        session.add_all(users)
        result = session.execute(select(User))
        db_users = result.scalars().all()
    user_dict = {
        u.email: {
            "email": u.email,
            "id": u.id,
            "is_superuser": u.is_superuser,
            "is_tenant_admin": u.is_tenant_admin,
            "tenant_id": u.tenant_id,
        }
        for u in db_users
    }
    yield user_dict
    session.execute(func.un0.test_set_mock_user_vars(*user_rluser_vars))
    session.execute(func.un0.set_role("writer"))
    session.execute(delete(User).where(User.email != sttngs.SUPERUSER_EMAIL))


@pytest.fixture(scope="session")
def data_dict(user_dict, tenant_dict, group_dict):
    yield {"users": user_dict, "tenants": tenant_dict, "groups": group_dict}
