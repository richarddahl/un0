# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore

from un0.auth.tables import User
from tests.conftest import mock_rls_vars
from un0.config import settings as sttngs


@pytest.fixture(scope="function")
def new_user(tenant_dict, group_dict):
    user = User(
        email="new_user@acme.com",
        handle="new_user",
        full_name="New User",
        tenant_id=tenant_dict.get("Acme Inc.").get("id"),
        default_group_id=group_dict.get("Acme Inc.").get("id"),
    )
    yield user


@pytest.fixture(scope="function")
def acme_admin(user_dict):
    yield user_dict.get("admin@acme.com")


@pytest.fixture(scope="function")
def acme_tenant(tenant_dict):
    yield tenant_dict.get("Acme Inc.")


@pytest.fixture(scope="function")
def nacme_tenant(tenant_dict):
    yield tenant_dict.get("Nacme Corp")


@pytest.fixture(scope="function")
def acme_group(group_dict):
    yield group_dict.get("Acme Inc.")


@pytest.fixture(scope="function")
def acme_admin_vars(acme_admin, acme_tenant):
    yield mock_rls_vars(
        acme_admin.get("id"),
        acme_admin.get("email"),
        "false",
        "true",
        acme_tenant.get("id"),
        role_name="writer",
    )
