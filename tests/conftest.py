# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
This module contains the global fixtures for the tests in all test modules.
Each test module has its own conftest.py file that containts the fixtures for that module.
"""

import textwrap
import pytest

from sqlalchemy import func, select, delete, text, create_engine
from sqlalchemy.orm import sessionmaker

from un0.cmd import create_db, drop_db
from un0.auth.models import Tenant, Group, User
from un0.auth.enums import TenantType
from un0.db.controller import DBController
from un0.config import settings as sttngs


###########################################
# SQL CONSTANTS FOR TESTING PURPOSES ONLY #
###########################################


CREATE_TEST_RAISE_CURRENT_ROLE_FUNCTION = """
CREATE OR REPLACE FUNCTION un0.testraise_role()
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    current_role VARCHAR;
BEGIN
    /*
    Function used to raise an exception to show the current role of the session
    Used for testing purposes
    */

    SELECT current_setting('role') INTO current_role;
    RAISE EXCEPTION 'Current role: %', current_role;
END;
$$;
"""


CREATE_TEST_LIST_USER_VARS_FUNCTION = """
CREATE OR REPLACE FUNCTION un0.testlist_rls_vars()
    RETURNS JSONB
    LANGUAGE plpgsql
AS $$
BEGIN
    /*
    Function to list the session variables used for RLS
    Used for testing purposes
    */
    RETURN jsonb_build_object(
        'id', current_setting('user_var.user_id', true),
        'email', current_setting('user_var.email', true),
        'is_superuser', current_setting('user_var.is_superuser', true),
        'is_tenant_admin', current_setting('user_var.is_tenant_admin', true),
        'tenant_id', current_setting('user_var.tenant_id', true)
    );
END;
$$;
"""


CREATE_TEST_MOCK_AUTHORIZE_USER_FUNCTION = """
CREATE OR REPLACE FUNCTION un0.mock_authorize_user(
    id VARCHAR,
    email VARCHAR,
    is_superuser VARCHAR,
    is_tenant_admin VARCHAR,
    tenant_id VARCHAR,
    role_name VARCHAR DEFAULT 'reader'
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
BEGIN
    /*
    Function to set the session variables used for RLS and set the role to the reader role
    */

    --Set the session variables
    PERFORM set_config('user_var.id', id, true);
    PERFORM set_config('user_var.email', email, true);
    PERFORM set_config('user_var.is_superuser', is_superuser, true);
    PERFORM set_config('user_var.is_tenant_admin', is_tenant_admin, true);
    PERFORM set_config('user_var.tenant_id', tenant_id, true);

    --Set the role to the databases reader role
    PERFORM un0.mock_role(role_name);
END;
$$;
"""


def create_mock_role_function():
    return textwrap.dedent(
        f"""
        CREATE OR REPLACE FUNCTION un0.mock_role(role_name VARCHAR)
        RETURNS VOID
        LANGUAGE plpgsql
        AS $$
        DECLARE
            full_role_name VARCHAR:= '{sttngs.DB_NAME}_' || role_name;
        BEGIN
            /*
            Function used to set the role of the current session to
            the appropriate role for the operation being performed.
            ADMIN for DDL
            READER for SELCT
            WRITER for INSERT, UPDATE, or DELETE
            LOGIN for login
            */

            IF role_name NOT IN ('admin', 'reader', 'writer', 'login') THEN
                RAISE EXCEPTION 'Invalid role name: %', role_name;
            END IF;
            EXECUTE 'SET ROLE ' || full_role_name;
        END;
        $$;
        """
    )


#############################
# FUNCTIONS CALLED BY TESTS #
#############################


def mock_rls_vars(
    id: str,
    email: str = sttngs.SUPERUSER_EMAIL,
    is_superuser: str = "true",
    is_tenant_admin: str = "false",
    tenant_id: str = "",
    role_name: str = "reader",
):
    return (id, email, is_superuser, is_tenant_admin, tenant_id, role_name)


############
# FIXTURES #
############


@pytest.fixture(scope="class")
def db_url():
    return f"{sttngs.DB_DRIVER}://{sttngs.DB_NAME}_login:{sttngs.DB_USER_PW}@{sttngs.DB_HOST}:{sttngs.DB_PORT}/{sttngs.DB_NAME}"


@pytest.fixture(scope="class")
def engine(db_url):
    yield create_engine(db_url)


@pytest.fixture(scope="class")
def superuser_id():
    """Creates the database and returns the superuser id."""
    db = DBController()
    db.drop_db()
    db.create_db()
    yield db.create_user(is_superuser=True)


@pytest.fixture(scope="class")
def session(engine, superuser_id, create_test_functions):
    session = sessionmaker(bind=engine, expire_on_commit=False)
    yield session()
    engine.dispose()


@pytest.fixture(scope="class")
def create_test_functions() -> None:
    eng = create_engine(
        f"{sttngs.DB_DRIVER}://{sttngs.DB_NAME}_login@/{sttngs.DB_NAME}"
    )
    with eng.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(f"SET ROLE {sttngs.DB_NAME}_admin"))
        conn.execute(text(create_mock_role_function()))
        conn.execute(text(CREATE_TEST_RAISE_CURRENT_ROLE_FUNCTION))
        conn.execute(text(CREATE_TEST_LIST_USER_VARS_FUNCTION))
        conn.execute(text(CREATE_TEST_MOCK_AUTHORIZE_USER_FUNCTION))


@pytest.fixture(scope="class")
def tenant_dict(session, superuser_id):
    """Creates tenants and returns a dictionary of tenant names and ids.
    Used in the following modules:
        pgjwt
        user
        tenant
        group
    """
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
        session.execute(func.un0.mock_authorize_user(*mock_rls_vars(superuser_id)))
        session.execute(func.un0.mock_role("writer"))
        session.add_all(tenants)
        result = session.execute(select(Tenant))
    db_tenants = result.scalars().all()
    tenant_dict = {
        t.name: {"id": t.id, "tenant_type": t.tenant_type} for t in db_tenants
    }
    yield tenant_dict


@pytest.fixture(scope="class")
def group_dict(session, superuser_id):
    with session.begin():
        session.execute(func.un0.mock_authorize_user(*mock_rls_vars(superuser_id)))
        result = session.execute(select(Group))
        db_groups = result.scalars().all()
        group_dict = {g.name: {"id": g.id} for g in db_groups}

    yield group_dict


@pytest.fixture(scope="class")
def user_dict(session, superuser_id, tenant_dict, group_dict):
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
        session.execute(func.un0.mock_authorize_user(*mock_rls_vars(superuser_id)))
        session.execute(func.un0.mock_role("writer"))
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


@pytest.fixture(scope="class")
def data_dict(user_dict, tenant_dict, group_dict):
    yield {"users": user_dict, "tenants": tenant_dict, "groups": group_dict}
