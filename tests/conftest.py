# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
#
# SPDX-License-Identifier: MIT

"""
This module contains the global fixtures for the tests in all test modules.
Each test module has its own conftest.py file that containts the fixtures for that module.
Each TestClass in a test module has its own setup_class and teardown_class methods.
The setup_class method is called before any tests in the class are run.
It creates a new database for that modules tests.
"""


import pytest

from un0.config import settings as sttngs


# Not a pytest.fixture as need to call it with various parameters for testing
def mock_session_variables_for_user(email, is_superuser, is_tenant_admin, tenant_id):
    """Mocks the session variables for a user."""
    return f"""
        SELECT SET_CONFIG('s_var.user_email', '{email}', true);
        SELECT SET_CONFIG('s_var.is_superuser', '{is_superuser}', true);
        SELECT SET_CONFIG('s_var.is_tenant_admin', '{is_tenant_admin}', true);
        SELECT SET_CONFIG('s_var.tenant_id', '{tenant_id}', true);
    """


# Fixtures start here
@pytest.fixture(scope="session")
def mock_superuser_session_variables():
    """Mocks the session variables for a superuser."""
    return f"""
        SELECT SET_CONFIG('s_var.user_email', '{sttngs.SUPERUSER_EMAIL}', true);
        SELECT SET_CONFIG('s_var.is_superuser', 'true', true);
        SELECT SET_CONFIG('s_var.is_tenant_admin', 'false', true);
        SELECT SET_CONFIG('s_var.tenant_id', '', true);
    """
