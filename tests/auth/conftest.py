# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore
from typing import Any

from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import sessionmaker

from un0.cmd import create_db, drop_db
from un0.cmd.sql import (
    set_role_admin,
    set_role_reader,
    set_role_writer,
)
from un0.config import settings as sttngs
from un0.auth.models import Tenant, Group, User
from un0.auth.enums import TenantType


@pytest.fixture(scope="class")
def db_name(request):
    db_name = request.param
    drop_db.drop(db_name=db_name)
    create_db.create(db_name=db_name)
    yield db_name
    # drop_db.drop(db_name=db)


@pytest.fixture(scope="function")
def session(request):
    db_name = request.param
    db_url = f"{sttngs.DB_DRIVER}://{db_name}_login:{sttngs.DB_USER_PW}@{sttngs.DB_HOST}:{sttngs.DB_PORT}/{db_name}"
    session = sessionmaker(create_engine(db_url), expire_on_commit=False)
    yield session()


@pytest.fixture(scope="function")
def admin_user(session, db_name, mock_su_s_vars):
    session.execute(text(mock_su_s_vars))
    session.execute(text(set_role_reader(db_name=db_name)))
    q = select(User).where(User.email == sttngs.SUPERUSER_EMAIL)
    result = session.execute(q)
    admin_user = result.scalars().first()
    return admin_user


@pytest.fixture(scope="function")
def tenant_dict(session, mock_su_s_vars, db_name):
    tenant_list = [
        ["Acme Inc.", TenantType.ENTERPRISE],
        ["Nacme Corp", TenantType.CORPORATE],
        ["Coyote LLP", TenantType.SMALL_BUSINESS],
        ["Birdy", TenantType.INDIVIDUAL],
    ]
    tenants = [
        Tenant(name=name, tenant_type=tenant_type) for name, tenant_type in tenant_list
    ]
    session.execute(text(mock_su_s_vars))
    session.execute(text(set_role_writer(db_name=db_name)))
    session.add_all(tenants)
    result = session.execute(select(Tenant))
    db_tenants = result.scalars().all()
    tenant_dict = {
        t.name: {"id": t.id, "tenant_type": t.tenant_type} for t in db_tenants
    }
    yield tenant_dict
    # session.execute(sa.text(mock_su_s_vars))
    # session.execute(sa.delete(Tenant).where(Tenant.id != ""))
    # session.commit()


@pytest.fixture(scope="function")
def group_dict(request, session, mock_su_s_vars, db_name, tenant_dict):
    session.execute(text(mock_su_s_vars))
    session.execute(text(set_role_writer(db_name=db_name)))
    result = session.execute(select(Group))
    db_groups = result.scalars().all()
    group_dict = {g.name: {"id": g.id} for g in db_groups}

    yield group_dict
    # session.execute(sa.text(mock_su_s_vars))
    # session.execute(sa.delete(Group).where(Group.id != ""))
    # session.commit()


@pytest.fixture(scope="function")
def user_dict(session, mock_su_s_vars, db_name, tenant_dict, group_dict):
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
    session.execute(text(mock_su_s_vars))
    session.execute(text(set_role_writer(db_name=db_name)))
    session.add_all(users)
    session.commit()
    session.execute(text(mock_su_s_vars))
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
    # session.execute(sa.text(mock_su_s_vars))
    # session.execute(sa.delete(User).where(User.email != sttngs.SUPERUSER_EMAIL))
    # session.commit()


@pytest.fixture(scope="function")
def data_dict(user_dict, tenant_dict, group_dict):
    yield {"users": user_dict, "tenants": tenant_dict, "groups": group_dict}
