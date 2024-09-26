# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore
from typing import Any

import sqlalchemy as sa

from un0.cmd.sql import (
    set_role_admin,
    set_role_reader,
    set_role_writer,
)
from un0.config import settings as sttngs
from un0.auth.models import Tenant, Group, User
from un0.auth.enums import TenantType


@pytest.fixture(scope="function")
def db_name() -> str:
    return "un0_test_auth"


@pytest.fixture(scope="function")
def db_url(db_name: str) -> str:
    return f"{sttngs.DB_DRIVER}://{db_name}_login:{sttngs.DB_USER_PW}@{sttngs.DB_HOST}:{sttngs.DB_PORT}/{db_name}"


@pytest.fixture(scope="function")
def session(db_url: str):
    session = sa.orm.sessionmaker(sa.create_engine(db_url))()
    yield session
    session.close()


@pytest.fixture(scope="function")
def data_for_tests(
    session: sa.orm.Session, mock_superuser_session_variables, db_name
) -> Generator[Any, Any, Any]:
    users = []
    session.execute(sa.text(mock_superuser_session_variables))
    session.execute(sa.text(set_role_writer(db_name=db_name)))
    tenant_data = [
        ["Acme Inc.", TenantType.ENTERPRISE],
        ["Nacme Corp", TenantType.CORPORATE],
        ["Coyote LLP", TenantType.SMALL_BUSINESS],
        ["Birdy", TenantType.INDIVIDUAL],
    ]
    tenants = [
        Tenant(name=name, tenant_type=tenant_type) for name, tenant_type in tenant_data
    ]
    session.add_all(tenants)
    session.commit()
    result = session.execute(sa.select(Tenant))
    db_tenants = result.scalars().all()
    tenant_dict = {
        t.name: {"id": t.id, "tenant_type": t.tenant_type} for t in db_tenants
    }

    result = session.execute(sa.select(Group))
    db_groups = result.scalars().all()
    group_dict = {g.name: {"id": g.id} for g in db_groups}

    for tenant in db_tenants:
        tenant_name = tenant.name.split(" ")[0].lower()
        tenant_id = tenant_dict.get(tenant.name).get("id")
        default_group_id = group_dict.get(tenant.name).get("id")
        users.append(
            User(
                email=f"{'admin'}@{tenant_name}.com",
                handle=f"{tenant_name}_admin",
                full_name=f"{tenant.name} Admin",
                is_tenant_admin=True,
                tenant_id=tenant_id,
                default_group_id=default_group_id,
            )
        )
        if tenant.tenant_type == TenantType.ENTERPRISE:
            rng = range(1, 10)
        elif tenant.tenant_type == TenantType.CORPORATE:
            rng = range(1, 5)
        elif tenant.tenant_type == TenantType.SMALL_BUSINESS:
            rng = range(1, 3)
        else:
            rng = range(1, 1)
        for u in rng:
            users.append(
                User(
                    email=f"{'User'}{u}@{tenant_name}.com",
                    handle=f"{tenant_name}_user{u}",
                    full_name=f"{tenant.name} User{u}",
                    tenant_id=tenant_id,
                    default_group_id=default_group_id,
                )
            )
    session.add_all(users)
    session.commit()

    result = session.execute(sa.select(User))
    db_users = result.scalars().all()
    user_dict = {
        u.email: {
            "id": u.id,
            "is_superuser": u.is_superuser,
            "is_tenant_admin": u.is_tenant_admin,
            "tenant_id": u.tenant_id,
        }
        for u in db_users
    }
    yield {"users": user_dict, "tenants": tenant_dict, "groups": group_dict}
    session.execute(sa.delete(User).where(User.id != ""))
    session.execute(sa.delete(Group).where(Group.id != ""))
    session.execute(sa.delete(Tenant).where(Tenant.id != ""))
    session.commit()
