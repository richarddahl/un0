# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
This module contains the global fixtures for the tests in all test modules.
Each test module has its own conftest.py file that containts the fixtures for that module.
"""

import pytest

from un0.config import settings as sttngs


# Not a pytest.fixture as need to call it with parameters not known until runtime
def mock_s_vars(
    email: str,
    is_superuser: str = "false",
    is_tenant_admin: str = "false",
    tenant_id: str = "",
):
    """Mocks the session variables for a user."""
    return f"""
        SELECT SET_CONFIG('s_var.user_email', '{email}', true);
        SELECT SET_CONFIG('s_var.is_superuser', '{is_superuser}', true);
        SELECT SET_CONFIG('s_var.is_tenant_admin', '{is_tenant_admin}', true);
        SELECT SET_CONFIG('s_var.tenant_id', '{tenant_id}', true);
    """


# Fixtures start here
@pytest.fixture(scope="session")
def mock_su_s_vars():
    """Mocks the session variables for a superuser."""
    return f"""
        SELECT SET_CONFIG('s_var.user_email', '{sttngs.SUPERUSER_EMAIL}', true);
        SELECT SET_CONFIG('s_var.is_superuser', 'true', true);
        SELECT SET_CONFIG('s_var.is_tenant_admin', 'false', true);
        SELECT SET_CONFIG('s_var.tenant_id', '', true);
    """
