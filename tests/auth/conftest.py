# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

import pytest  # type: ignore

from sqlalchemy import func, select

from un0.auth.models import User
from un0.config import settings as sttngs

from tests.conftest import get_mock_user_vars


@pytest.fixture(scope="session")
def db_name():
    return "un0_test_auth"


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
